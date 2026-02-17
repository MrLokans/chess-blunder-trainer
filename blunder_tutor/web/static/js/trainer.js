import { bus } from './event-bus.js';
import { WebSocketClient } from './websocket-client.js';
import { client, ApiError } from './api.js';
import { BoardAdapter } from './trainer/board-adapter.js';
import { updateEvalBar } from './trainer/eval-bar.js';
import * as state from './trainer/state.js';
import * as ui from './trainer/ui.js';
import * as filters from './trainer/filters.js';
import * as visuals from './trainer/board-visuals.js';
import * as linePlayer from './trainer/line-player.js';
import { initKeyboard } from './trainer/keyboard.js';
import { initVimInput, show as showVimInput } from './trainer/vim-input.js';

const wsClient = new WebSocketClient();

function getLastMove() {
  const game = state.get('game');
  const history = game.history({ verbose: true });
  return history.length > 0 ? history[history.length - 1] : null;
}

function onBoardMove(_orig, _dest, move) {
  if (state.get('animatingLine')) return;
  const game = state.get('game');
  ui.updateCurrentMove(game);
  state.get('board').clearArrows();
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
      ui.getEl('submitBtn').classList.remove('hidden');
    }
  }
}

async function loadPuzzle() {
  if (state.get('animatingLine')) return;
  state.resetForNewPuzzle();
  linePlayer.clearLineNavigation();
  ui.resetUIForNewPuzzle();
  filters.updateFilterCountBadge();

  try {
    const data = await client.trainer.getPuzzle(filters.getFilterParams());
    setupPuzzle(data);
  } catch (err) {
    handleLoadError(err);
  }
}

async function loadSpecificPuzzle(gameId, ply) {
  state.resetForNewPuzzle();
  linePlayer.clearLineNavigation();
  ui.resetUIForNewPuzzle();

  try {
    const data = await client.trainer.getSpecificPuzzle(gameId, parseInt(ply, 10));
    setupPuzzle(data);
  } catch (err) {
    console.error('Failed to load specific puzzle:', err);
    ui.showEmptyState('unknown');
  }
}

function setupPuzzle(data) {
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

  const board = new BoardAdapter('board', {
    fen: data.fen,
    orientation,
    game,
    onMove: onBoardMove,
  });
  state.set('board', board);

  ui.updateColorBadge(data.player_color);
  ui.updatePhaseBadge(data.game_phase);
  ui.updateTacticalBadge(data.tactical_pattern);
  ui.updateGameLink(data.game_url);
  ui.updateCopyDebugBtn(data.game_id, data.ply);
  ui.updateStarButton(
    data.game_id, data.ply,
    () => state.get('currentStarred'),
    (v) => state.set('currentStarred', v),
  );
  ui.showPuzzleData(data);
  updateEvalBar(data.eval_before, data.player_color, ui.getEl('evalBarFill'), ui.getEl('evalValue'));

  setTimeout(() => {
    visuals.redrawAllHighlights();
    visuals.redrawArrows();
  }, 100);
}

async function hasActiveJobs() {
  try {
    const jobs = await client.jobs.list({ status: 'running' });
    if (Array.isArray(jobs) && jobs.length > 0) return true;
    const pending = await client.jobs.list({ status: 'pending' });
    return Array.isArray(pending) && pending.length > 0;
  } catch {
    return false;
  }
}

async function handleLoadError(err) {
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

let analyzingRetryTimer = null;

function scheduleAnalyzingRetry() {
  if (analyzingRetryTimer) clearTimeout(analyzingRetryTimer);
  analyzingRetryTimer = setTimeout(() => {
    analyzingRetryTimer = null;
    loadPuzzle();
  }, 5000);
}

async function submitMoveAction() {
  if (state.get('animatingLine')) return;
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
    best_move_eval: puzzle.best_move_eval || null,
  };

  try {
    const data = await client.trainer.submitMove(payload);
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
    ui.showBoardResult('accent-revealed', t('trainer.feedback.error'), err.message || t('trainer.feedback.submit_failed'));
    console.error(err);
  }
}

function revealBestMove() {
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

function resetPosition() {
  if (state.get('animatingLine')) return;
  const puzzle = state.get('puzzle');
  if (!puzzle) return;

  const game = new Chess(puzzle.fen);
  state.set('game', game);
  state.get('board').setPosition(puzzle.fen, game);
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

function undoMove() {
  if (state.get('animatingLine')) return;
  const game = state.get('game');
  if (game.history().length === 0) return;
  game.undo();
  state.get('board').setPosition(game.fen(), game);
  state.popMove();
  ui.updateMoveHistory(state.get('moveHistory'));
  ui.updateCurrentMove(game);
}

function openLichessAnalysis() {
  const puzzle = state.get('puzzle');
  if (!puzzle) return;
  const game = state.get('game');
  const fen = game.fen();
  const encodedFen = fen.replace(/ /g, '_');
  const color = puzzle.player_color;

  const arrows = [];
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

function flipBoard() {
  const board = state.get('board');
  const puzzle = state.get('puzzle');
  if (!board || !puzzle) return;
  const flipped = !state.get('boardFlipped');
  state.set('boardFlipped', flipped);
  const base = puzzle.player_color === 'black' ? 'black' : 'white';
  board.setOrientation(flipped ? (base === 'white' ? 'black' : 'white') : base);
}

// --- Wire up event bus actions ---

bus.on('action:submit', submitMoveAction);
bus.on('action:next', () => { trackEvent('Puzzle Next'); loadPuzzle(); });
bus.on('action:reset', resetPosition);
bus.on('action:undo', () => { trackEvent('Puzzle Undo'); undoMove(); });
bus.on('action:flip', () => { trackEvent('Board Flipped'); flipBoard(); });
bus.on('action:lichess', openLichessAnalysis);
bus.on('action:playBest', () => { trackEvent('Puzzle Try Best'); linePlayer.playBestMove(); });
bus.on('action:reveal', () => {
  if (state.get('bestRevealed')) {
    ui.toggleBoardResultOverlay();
  } else {
    trackEvent('Puzzle Best Move Revealed');
    ui.showBoardResult('accent-revealed', t('trainer.feedback.best_revealed'), t('trainer.feedback.best_revealed_detail'));
    revealBestMove();
  }
});

bus.on('action:vimInput', () => {
  if (!state.get('animatingLine') && !state.get('submitted') && state.get('puzzle')) {
    showVimInput();
  }
});

bus.on('filters:changed', (detail) => {
  trackEvent('Filter Changed', { filter_type: detail?.filterType || '' });
  loadPuzzle();
});

// --- Wire up DOM event listeners ---

function initEventListeners() {
  const el = ui.getEl.bind(ui);

  el('submitBtn').addEventListener('click', (e) => { e.stopPropagation(); submitMoveAction(); });
  el('resetBtn').addEventListener('click', resetPosition);
  el('showBestBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    bus.emit('action:reveal');
  });
  el('nextBtn').addEventListener('click', loadPuzzle);
  el('tryBestBtn').addEventListener('click', () => linePlayer.playBestMove());
  el('overlayNextBtn').addEventListener('click', (e) => { e.stopPropagation(); loadPuzzle(); });
  el('undoBtn').addEventListener('click', undoMove);
  el('lichessBtn').addEventListener('click', openLichessAnalysis);

  const shortcutsClose = el('shortcutsClose');
  const shortcutsOverlay = el('shortcutsOverlay');
  const shortcutsHintBtn = el('shortcutsHintBtn');

  if (shortcutsClose) shortcutsClose.addEventListener('click', ui.toggleShortcutsOverlay);
  if (shortcutsOverlay) {
    shortcutsOverlay.addEventListener('click', (e) => {
      if (e.target === shortcutsOverlay) ui.toggleShortcutsOverlay();
    });
  }
  if (shortcutsHintBtn) shortcutsHintBtn.addEventListener('click', ui.toggleShortcutsOverlay);

  document.addEventListener('click', (e) => {
    if (!ui.isBoardResultVisible()) return;
    const boardResultCard = el('boardResultCard');
    const inner = boardResultCard.querySelector('.board-result-inner');
    if (inner && !inner.contains(e.target)) {
      ui.hideBoardResult();
    }
  });

  const showArrowsEl = el('showArrows');
  const showThreatsEl = el('showThreats');
  const showTacticsEl = el('showTactics');
  if (showArrowsEl) showArrowsEl.addEventListener('change', () => visuals.redrawArrows());
  if (showThreatsEl) showThreatsEl.addEventListener('change', () => visuals.redrawAllHighlights());
  if (showTacticsEl) showTacticsEl.addEventListener('change', () => visuals.redrawAllHighlights());
}

// --- Initialize ---

async function init() {
  ui.initUI();
  filters.initFilters();
  initKeyboard();
  initVimInput({
    getGame: () => state.get('game'),
    getBoard: () => state.get('board'),
    isInteractive: () => !state.get('animatingLine') && !state.get('submitted') && !!state.get('puzzle'),
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
  htmx.trigger('#statsContent', 'statsUpdate');
});
