import { bus } from '../shared/event-bus';
import { WebSocketClient } from '../shared/websocket-client';
import { client, ApiError } from '../shared/api';
import { BoardAdapter } from './board-adapter';
import { updateEvalBar } from './eval-bar';
import * as state from './state';
import type { PuzzleData } from './state';
import * as ui from './ui';
import * as filters from './filters';
import * as visuals from './board-visuals';
import * as linePlayer from './line-player';
import { initKeyboard } from './keyboard';
import { initVimInput, show as showVimInput } from './vim-input';

interface SubmitResponse {
  is_best: boolean;
  is_blunder: boolean;
  user_san: string;
  user_eval: number;
  user_eval_display: string;
  user_uci: string;
}

const wsClient = new WebSocketClient();

function getLastMove(): { san: string; from: string; to: string; promotion?: string } | undefined {
  const game = state.get('game');
  if (!game) return undefined;
  const history = game.history({ verbose: true });
  return history.length > 0 ? history[history.length - 1] : undefined;
}

function onBoardMove(_orig: string, _dest: string, move: { san: string; from: string; to: string; promotion?: string }): void {
  if (state.isAnimating()) return;
  const game = state.get('game');
  if (!game) return;
  ui.updateCurrentMove(game);
  state.get('board')?.clearArrows();
  setTimeout(() => visuals.redrawAllHighlights(), 50);
  ui.dimBlunderSection();

  if (state.get('bestRevealed')) {
    state.pushMove(move.san);
    ui.updateMoveHistory(state.get('moveHistory'));
    ui.showHistorySection();
  } else if (!state.get('submitted')) {
    const puzzle = state.get('puzzle');
    const uci = move.from + move.to + (move.promotion || '');
    if (puzzle && uci === puzzle.best_move_uci) {
      setTimeout(() => submitMoveAction(), 150);
    } else {
      const submitBtn = ui.getEl('submitBtn');
      if (submitBtn) submitBtn.classList.remove('hidden');
    }
  }
}

let _loadCooldown = false;

async function loadPuzzle(): Promise<void> {
  if (state.isAnimating() || _loadCooldown) return;
  _loadCooldown = true;
  setTimeout(() => { _loadCooldown = false; }, 500);
  state.resetForNewPuzzle();
  linePlayer.clearLineNavigation();
  ui.resetUIForNewPuzzle();
  filters.updateFilterCountBadge();

  try {
    const data = await client.trainer.getPuzzle(filters.getFilterParams()) as PuzzleData;
    setupPuzzle(data);
  } catch (err) {
    handleLoadError(err);
  }
}

async function loadSpecificPuzzle(gameId: string, ply: string): Promise<void> {
  if (state.isAnimating()) return;
  state.resetForNewPuzzle();
  linePlayer.clearLineNavigation();
  ui.resetUIForNewPuzzle();

  try {
    const data = await client.trainer.getSpecificPuzzle(gameId, parseInt(ply, 10)) as PuzzleData;
    setupPuzzle(data);
  } catch (err) {
    console.error('Failed to load specific puzzle:', err);
    ui.showEmptyState('unknown');
  }
}

function setupPuzzle(data: PuzzleData): void {
  ui.hideEmptyState();
  state.set('puzzle', data);
  trackEvent('Puzzle Loaded', {
    phase: data.game_phase || '',
    color: data.player_color || '',
    difficulty: data.difficulty || '',
    tactical_pattern: data.tactical_pattern || '',
  });
  const game = new Chess(data.fen);
  state.set('game', game);

  const orientation = data.player_color === 'black' ? 'black' : 'white';
  const oldBoard = state.get('board');
  if (oldBoard) oldBoard.destroy();

  const shouldAnimate = data.pre_move_uci
    && data.pre_move_fen
    && window.__features
    && window.__features['trainer.pre_move'];

  const board = new BoardAdapter('board', {
    fen: shouldAnimate ? data.pre_move_fen! : data.fen,
    orientation,
    game,
    onMove: onBoardMove,
    coordinates: filters.getShowCoordinates(),
    interactive: !shouldAnimate,
  });
  state.set('board', board);

  ui.updateColorBadge(data.player_color);
  ui.updatePhaseBadge(data.game_phase);
  ui.updateTacticalBadge(data.tactical_pattern);
  ui.updateGameLink(data.game_url);
  ui.updateCopyDebugBtn(data.game_id, data.ply);
  ui.updateReviewGameLink(data.game_id, data.ply);
  ui.updateStarButton(
    data.game_id, data.ply,
    () => state.get('currentStarred'),
    (v) => state.set('currentStarred', v),
  );
  ui.showPuzzleData(data);
  const evalBarFill = ui.getEl('evalBarFill');
  const evalValue = ui.getEl('evalValue');
  if (evalBarFill && evalValue) {
    updateEvalBar(data.eval_before, data.player_color, evalBarFill, evalValue);
  }

  if (shouldAnimate) {
    const from = data.pre_move_uci!.slice(0, 2);
    const to = data.pre_move_uci!.slice(2, 4);
    state.set('animatingPreMove', true);
    board.animatePreMove(data.fen, from, to, game, () => {
      state.set('animatingPreMove', false);
      setTimeout(() => {
        visuals.redrawAllHighlights();
        visuals.redrawArrows();
      }, 100);
    });
  } else {
    setTimeout(() => {
      visuals.redrawAllHighlights();
      visuals.redrawArrows();
    }, 100);
  }
}

async function hasActiveJobs(): Promise<boolean> {
  try {
    const jobs = await client.jobs.list({ status: 'running' });
    if (Array.isArray(jobs) && jobs.length > 0) return true;
    const pending = await client.jobs.list({ status: 'pending' });
    return Array.isArray(pending) && pending.length > 0;
  } catch {
    return false;
  }
}

async function handleLoadError(err: unknown): Promise<void> {
  if (err instanceof ApiError) {
    const msg = err.message.toLowerCase();
    if (msg.includes('no games found') || msg.includes('no blunders found')) {
      const active = await hasActiveJobs();
      if (active) {
        ui.showEmptyState('analyzing');
        scheduleAnalyzingRetry();
        return;
      }
      if (msg.includes('no games found')) {
        ui.showEmptyState('no_games');
      } else {
        ui.showEmptyState(
          filters.hasActiveFilters() ? 'no_blunders_filtered' : 'no_blunders',
          filters.clearAllFilters,
        );
      }
    } else {
      ui.showEmptyState('unknown');
    }
  } else {
    console.error('Failed to load puzzle:', err);
    ui.showEmptyState('unknown');
  }
}

let analyzingRetryTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleAnalyzingRetry(): void {
  if (analyzingRetryTimer) clearTimeout(analyzingRetryTimer);
  analyzingRetryTimer = setTimeout(() => {
    analyzingRetryTimer = null;
    loadPuzzle();
  }, 5000);
}

async function submitMoveAction(): Promise<void> {
  if (state.isAnimating()) return;
  const puzzle = state.get('puzzle');
  const game = state.get('game');
  if (!puzzle || !game) return;

  const lastMove = getLastMove();
  if (!lastMove) {
    ui.showBoardResult('accent-revealed', t('common.no_move_made'), t('trainer.feedback.no_move'));
    return;
  }

  const uci = lastMove.from + lastMove.to + (lastMove.promotion || '');
  const payload = {
    move: uci,
    fen: puzzle.fen || '',
    game_id: puzzle.game_id || '',
    ply: puzzle.ply || 0,
    blunder_uci: puzzle.blunder_uci || '',
    blunder_san: puzzle.blunder_san || '',
    best_move_uci: puzzle.best_move_uci || '',
    best_move_san: puzzle.best_move_san || '',
    best_line: puzzle.best_line || [],
    player_color: puzzle.player_color || 'white',
    eval_after: puzzle.eval_after || 0,
    best_move_eval: puzzle.best_move_eval ?? null,
  };

  ui.showSubmitting();
  try {
    const data = await client.trainer.submitMove(payload) as SubmitResponse;
    ui.hideSubmitting();
    state.set('submitted', true);

    trackEvent('Puzzle Submitted', {
      result: data.is_best ? 'correct' : 'incorrect',
      phase: puzzle.game_phase || '',
      difficulty: puzzle.difficulty || '',
    });

    if (data.is_best) {
      ui.showCorrectFeedback();
    } else if (data.is_blunder) {
      ui.showBlunderFeedback(data.user_san);
    } else {
      const evalDiff = Math.abs(data.user_eval - puzzle.eval_before);
      if (evalDiff < 50) {
        ui.showGoodMoveFeedback(data.user_san);
      } else {
        ui.showNotQuiteFeedback(data.user_san, data.user_eval_display);
      }
      visuals.redrawAllHighlightsWithUser(data.user_uci);
    }

    ui.showLegendBest();
    revealBestMove();

    if (data.is_best || data.is_blunder) {
      visuals.redrawAllHighlights();
    }

    if (typeof htmx !== 'undefined') {
      htmx.trigger(document.body, 'statsUpdate');
    }
  } catch (err) {
    ui.hideSubmitting();
    const errMsg = err instanceof Error ? err.message : t('trainer.feedback.submit_failed');
    ui.showBoardResult('accent-revealed', t('trainer.feedback.error'), errMsg);
    console.error(err);
  }
}

function revealBestMove(): void {
  state.set('bestRevealed', true);
  ui.enterExplorePhase();

  const puzzle = state.get('puzzle');
  if (puzzle) {
    ui.showTacticalInfo(puzzle.tactical_pattern, puzzle.tactical_reason);
    ui.showExplanation(puzzle.explanation_blunder, puzzle.explanation_best);
    const tactical = visuals.redrawAllHighlights();
    if (tactical && tactical.size > 0) ui.showLegendTactic();
  }

  visuals.redrawArrows();
}

function resetPosition(): void {
  if (state.isAnimating()) return;
  const puzzle = state.get('puzzle');
  if (!puzzle) return;

  const game = new Chess(puzzle.fen);
  state.set('game', game);
  const board = state.get('board');
  if (board) board.setPosition(puzzle.fen, game);
  ui.updateCurrentMove(game);
  state.set('moveHistory', []);
  linePlayer.clearLineNavigation();
  ui.updateMoveHistory([]);

  if (!state.get('bestRevealed')) {
    ui.hideBoardResult();
  }

  setTimeout(() => {
    visuals.redrawAllHighlights();
    visuals.redrawArrows();
  }, 50);
}

function undoMove(): void {
  if (state.isAnimating()) return;
  const game = state.get('game');
  if (!game || game.history().length === 0) return;
  game.undo();
  const board = state.get('board');
  if (board) board.setPosition(game.fen(), game);
  state.popMove();
  ui.updateMoveHistory(state.get('moveHistory'));
  ui.updateCurrentMove(game);
}

function openLichessAnalysis(): void {
  const puzzle = state.get('puzzle');
  if (!puzzle) return;
  const game = state.get('game');
  if (!game) return;
  const fen = game.fen();
  const encodedFen = fen.replace(/ /g, '_');
  const color = puzzle.player_color;

  const arrows: string[] = [];
  if (game.fen() === puzzle.fen) {
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      arrows.push(`R${puzzle.blunder_uci.slice(0, 2)}${puzzle.blunder_uci.slice(2, 4)}`);
    }
    if (puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      arrows.push(`G${puzzle.best_move_uci.slice(0, 2)}${puzzle.best_move_uci.slice(2, 4)}`);
    }
  }

  const arrowHash = arrows.length > 0 ? '#' + arrows.join(',') : '';
  window.open(`https://lichess.org/analysis/${encodedFen}?color=${color}${arrowHash}`, '_blank');
}

function flipBoard(): void {
  const board = state.get('board');
  const puzzle = state.get('puzzle');
  if (!board || !puzzle) return;
  const flipped = !state.get('boardFlipped');
  state.set('boardFlipped', flipped);
  const base = puzzle.player_color === 'black' ? 'black' : 'white';
  board.setOrientation(flipped ? (base === 'white' ? 'black' : 'white') : base);
}

bus.on('action:submit' as never, submitMoveAction as never);
bus.on('action:next' as never, (() => { trackEvent('Puzzle Next'); loadPuzzle(); }) as never);
bus.on('action:reset' as never, resetPosition as never);
bus.on('action:undo' as never, (() => { trackEvent('Puzzle Undo'); undoMove(); }) as never);
bus.on('action:flip' as never, (() => { trackEvent('Board Flipped'); flipBoard(); }) as never);
bus.on('action:lichess' as never, openLichessAnalysis as never);
bus.on('action:playBest' as never, (() => { trackEvent('Puzzle Try Best'); linePlayer.playBestMove(); }) as never);
bus.on('action:reveal' as never, (() => {
  if (state.get('bestRevealed')) {
    ui.toggleBoardResultOverlay();
  } else {
    trackEvent('Puzzle Best Move Revealed');
    ui.showBoardResult('accent-revealed', t('trainer.feedback.best_revealed'), t('trainer.feedback.best_revealed_detail'));
    revealBestMove();
  }
}) as never);

bus.on('action:vimInput' as never, (() => {
  if (!state.isAnimating() && !state.get('submitted') && state.get('puzzle')) {
    showVimInput();
  }
}) as never);

bus.on('filters:changed' as never, ((detail: { filterType?: string } | undefined) => {
  trackEvent('Filter Changed', { filter_type: detail?.filterType || '' });
  loadPuzzle();
}) as never);

function initEventListeners(): void {
  const submitBtn = ui.getEl('submitBtn');
  const resetBtn = ui.getEl('resetBtn');
  const showBestBtn = ui.getEl('showBestBtn');
  const nextBtn = ui.getEl('nextBtn');
  const tryBestBtn = ui.getEl('tryBestBtn');
  const overlayNextBtn = ui.getEl('overlayNextBtn');
  const undoBtn = ui.getEl('undoBtn');
  const lichessBtn = ui.getEl('lichessBtn');

  if (submitBtn) submitBtn.addEventListener('click', (e) => { e.stopPropagation(); submitMoveAction(); });
  if (resetBtn) resetBtn.addEventListener('click', resetPosition);
  if (showBestBtn) showBestBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    bus.emit('action:reveal' as never);
  });
  if (nextBtn) nextBtn.addEventListener('click', () => loadPuzzle());
  if (tryBestBtn) tryBestBtn.addEventListener('click', () => linePlayer.playBestMove());
  if (overlayNextBtn) overlayNextBtn.addEventListener('click', (e) => { e.stopPropagation(); loadPuzzle(); });
  if (undoBtn) undoBtn.addEventListener('click', undoMove);
  if (lichessBtn) lichessBtn.addEventListener('click', openLichessAnalysis);

  const shortcutsClose = ui.getEl('shortcutsClose');
  const shortcutsOverlay = ui.getEl('shortcutsOverlay');
  const shortcutsHintBtn = ui.getEl('shortcutsHintBtn');

  if (shortcutsClose) shortcutsClose.addEventListener('click', ui.toggleShortcutsOverlay);
  if (shortcutsOverlay) {
    shortcutsOverlay.addEventListener('click', (e) => {
      if (e.target === shortcutsOverlay) ui.toggleShortcutsOverlay();
    });
  }
  if (shortcutsHintBtn) shortcutsHintBtn.addEventListener('click', ui.toggleShortcutsOverlay);

  document.addEventListener('click', (e) => {
    if (!ui.isBoardResultVisible()) return;
    const boardResultCard = ui.getEl('boardResultCard');
    if (!boardResultCard) return;
    const inner = boardResultCard.querySelector('.board-result-inner');
    if (inner && !inner.contains(e.target as Node)) {
      ui.hideBoardResult();
    }
  });

  const showArrowsEl = ui.getEl('showArrows');
  const showThreatsEl = ui.getEl('showThreats');
  const showTacticsEl = ui.getEl('showTactics');
  if (showArrowsEl) showArrowsEl.addEventListener('change', () => visuals.redrawArrows());
  if (showThreatsEl) showThreatsEl.addEventListener('change', () => visuals.redrawAllHighlights());
  if (showTacticsEl) showTacticsEl.addEventListener('change', () => visuals.redrawAllHighlights());

  bus.on('coordinates:changed' as never, (() => {
    const board = state.get('board');
    if (board) board.setCoordinates(filters.getShowCoordinates());
  }) as never);
}

async function init(): Promise<void> {
  ui.initUI();
  filters.initFilters();
  initKeyboard();
  initVimInput({
    getGame: () => state.get('game'),
    getBoard: () => state.get('board'),
    isInteractive: () => !state.isAnimating() && !state.get('submitted') && !!state.get('puzzle'),
    onMoveComplete: (move) => {
      onBoardMove(move.from, move.to, move);
    },
  });
  initEventListeners();

  await visuals.loadBoardSettings();

  const urlParams = new URLSearchParams(window.location.search);
  const deepGameId = urlParams.get('game_id');
  const deepPly = urlParams.get('ply');

  if (deepGameId && deepPly) {
    await loadSpecificPuzzle(deepGameId, deepPly);
  } else {
    loadPuzzle();
  }
}

init();

wsClient.connect();
wsClient.subscribe(['stats.updated']);
wsClient.on('stats.updated', () => {
  htmx.trigger(document.querySelector('#statsContent') ?? document.body, 'statsUpdate');
});
