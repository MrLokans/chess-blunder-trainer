import { WebSocketClient } from './websocket-client.js';
import { FilterPersistence } from './filter-persistence.js';
import { client, ApiError } from './api.js';
import { BoardAdapter } from './trainer/board-adapter.js';
import { buildThreatHighlights } from './trainer/threats.js';
import { updateEvalBar } from './trainer/eval-bar.js';
import {
  buildBlunderHighlight, buildBestMoveHighlight, buildUserMoveHighlight,
  buildTacticalHighlights, mergeHighlights
} from './trainer/highlights.js';

const wsClient = new WebSocketClient();

// State
let board = null;
let game = null;
let puzzle = null;
let submitted = false;
let bestRevealed = false;
let moveHistory = [];
let currentPhaseFilters = [];
let currentTacticalFilter = 'all';
let currentGameTypeFilters = [];
let currentColorFilter = 'both';
let currentDifficultyFilters = [];
let filtersCollapsed = false;
let boardFlipped = false;

let boardSettings = {
  piece_set: 'wikipedia',
  board_light: '#E8E4DB',
  board_dark: '#B8B4AB'
};

// DOM elements
const evalBarFill = document.getElementById('evalBarFill');
const evalValue = document.getElementById('evalValue');
const phaseIndicator = document.getElementById('phaseIndicator');
const colorBadge = document.getElementById('colorBadge');
const blunderMove = document.getElementById('blunderMove');
const evalBefore = document.getElementById('evalBefore');
const evalAfter = document.getElementById('evalAfter');
const cpLoss = document.getElementById('cpLoss');
const boardResultCard = document.getElementById('boardResultCard');
const feedbackTitle = document.getElementById('feedbackTitle');
const feedbackDetail = document.getElementById('feedbackDetail');
const movePrompt = document.getElementById('movePrompt');
const currentMoveEl = document.getElementById('currentMove');
const bestMoveDisplay = document.getElementById('bestMoveDisplay');
const bestLineDisplay = document.getElementById('bestLineDisplay');
const tacticalDetails = document.getElementById('tacticalDetails');
const explanationDetails = document.getElementById('explanationDetails');
const historySection = document.getElementById('historySection');
const moveHistoryEl = document.getElementById('moveHistory');

const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');
const showBestBtn = document.getElementById('showBestBtn');
const nextBtn = document.getElementById('nextBtn');
const tryBestBtn = document.getElementById('tryBestBtn');
const overlayNextBtn = document.getElementById('overlayNextBtn');
const undoBtn = document.getElementById('undoBtn');
const lichessBtn = document.getElementById('lichessBtn');
const highlightLegend = document.getElementById('highlightLegend');
const legendBlunder = document.getElementById('legendBlunder');
const legendBest = document.getElementById('legendBest');
const legendUser = document.getElementById('legendUser');
const showArrowsCheckbox = document.getElementById('showArrows');
const showThreatsCheckbox = document.getElementById('showThreats');
const phaseFilterCheckboxes = document.querySelectorAll('.phase-filter-checkbox');
const phaseBadge = document.getElementById('phaseBadge');
const tacticalBadge = document.getElementById('tacticalBadge');
const tacticalPatternName = document.getElementById('tacticalPatternName');
const tacticalInfoTitle = document.getElementById('tacticalInfoTitle');
const tacticalInfoReason = document.getElementById('tacticalInfoReason');
const tacticalFilterBtns = document.querySelectorAll('.tactical-filter-btn');
const showTacticsCheckbox = document.getElementById('showTactics');
const legendTactic = document.getElementById('legendTactic');
const gameTypeCheckboxes = document.querySelectorAll('.game-type-checkbox');
const colorFilterRadios = document.querySelectorAll('input[name="colorFilter"]');
const difficultyFilterCheckboxes = document.querySelectorAll('.difficulty-filter-checkbox');
const explanationBlunder = document.getElementById('explanationBlunder');
const explanationBest = document.getElementById('explanationBest');
const filtersHeader = document.getElementById('filtersHeader');
const filtersToggleBtn = document.getElementById('filtersToggleBtn');
const filtersContent = document.getElementById('filtersContent');
const filtersChevron = document.getElementById('filtersChevron');
const boardSettingsHeader = document.getElementById('boardSettingsHeader');
const boardSettingsContent = document.getElementById('boardSettingsContent');
const boardSettingsChevron = document.getElementById('boardSettingsChevron');
const emptyState = document.getElementById('emptyState');
const trainerLayout = document.getElementById('trainerLayout');
const emptyStateTitle = document.getElementById('emptyStateTitle');
const emptyStateMessage = document.getElementById('emptyStateMessage');
const emptyStateAction = document.getElementById('emptyStateAction');
const statsCard = document.getElementById('statsCard');
const sessionBar = document.getElementById('sessionBar');
const shortcutsOverlay = document.getElementById('shortcutsOverlay');
const shortcutsClose = document.getElementById('shortcutsClose');
const shortcutsHintBtn = document.getElementById('shortcutsHintBtn');
const blunderSection = document.getElementById('blunderSection');

// Board background SVG generation
let boardStyleEl = null;

function applyBoardBackground(light, dark) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">` +
    `<rect width="8" height="8" fill="${light}"/>` +
    Array.from({ length: 64 }, (_, i) => {
      const x = i % 8, y = Math.floor(i / 8);
      return (x + y) % 2 === 1 ? `<rect x="${x}" y="${y}" width="1" height="1" fill="${dark}"/>` : '';
    }).join('') +
    `</svg>`;

  const encoded = 'data:image/svg+xml;base64,' + btoa(svg);
  const css = `cg-board { background-image: url("${encoded}") !important; }`;

  if (!boardStyleEl) {
    boardStyleEl = document.createElement('style');
    boardStyleEl.id = 'cg-board-bg';
    document.head.appendChild(boardStyleEl);
  }
  boardStyleEl.textContent = css;
}

// Piece set style injection
let pieceStyleEl = null;

function applyPieceSet(pieceSet) {
  const format = pieceSet === 'wikipedia' ? 'png' : 'svg';
  const pieces = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
  const colorMap = { white: 'w', black: 'b' };
  const pieceMap = { pawn: 'P', rook: 'R', knight: 'N', bishop: 'B', queen: 'Q', king: 'K' };

  let css = '';
  for (const color of ['white', 'black']) {
    for (const role of pieces) {
      const file = `${colorMap[color]}${pieceMap[role]}`;
      const url = `/static/pieces/${pieceSet}/${file}.${format}`;
      css += `.cg-wrap piece.${role}.${color} { background-image: url(${url}); }\n`;
      css += `.cg-wrap piece.ghost.${role}.${color} { background-image: url(${url}); }\n`;
    }
  }

  if (!pieceStyleEl) {
    pieceStyleEl = document.createElement('style');
    pieceStyleEl.id = 'cg-piece-set';
    document.head.appendChild(pieceStyleEl);
  }
  pieceStyleEl.textContent = css;
}

function redrawAllHighlights() {
  if (!board || !puzzle) return;

  const blunder = buildBlunderHighlight(puzzle);
  const best = bestRevealed ? buildBestMoveHighlight(puzzle) : new Map();
  const threats = buildThreatHighlights(game, showThreatsCheckbox ? showThreatsCheckbox.checked : false);
  const tactical = buildTacticalHighlights(puzzle, game, bestRevealed,
    showTacticsCheckbox ? showTacticsCheckbox.checked : false);

  if (bestRevealed && tactical.size > 0 && legendTactic) {
    legendTactic.style.display = 'flex';
  }

  const merged = mergeHighlights(blunder, best, threats, tactical);
  board.setCustomHighlight(merged.size > 0 ? merged : undefined);
}

function redrawAllHighlightsWithUser(userUci) {
  if (!board || !puzzle) return;

  const blunder = buildBlunderHighlight(puzzle);
  const best = buildBestMoveHighlight(puzzle);
  const user = buildUserMoveHighlight(userUci);
  const threats = buildThreatHighlights(game, showThreatsCheckbox ? showThreatsCheckbox.checked : false);
  const tactical = buildTacticalHighlights(puzzle, game, bestRevealed,
    showTacticsCheckbox ? showTacticsCheckbox.checked : false);

  if (bestRevealed && tactical.size > 0 && legendTactic) {
    legendTactic.style.display = 'flex';
  }

  const merged = mergeHighlights(blunder, best, user, threats, tactical);
  board.setCustomHighlight(merged.size > 0 ? merged : undefined);
}

function redrawArrows() {
  if (!board || !puzzle) return;
  if (showArrowsCheckbox && !showArrowsCheckbox.checked) {
    board.clearArrows();
    return;
  }

  const atOriginalPosition = game.fen() === puzzle.fen;
  const arrows = [];

  if (atOriginalPosition) {
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      arrows.push({
        from: puzzle.blunder_uci.slice(0, 2),
        to: puzzle.blunder_uci.slice(2, 4),
        color: 'red'
      });
    }
    if (bestRevealed && puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      arrows.push({
        from: puzzle.best_move_uci.slice(0, 2),
        to: puzzle.best_move_uci.slice(2, 4),
        color: 'green'
      });
    }
  }

  if (arrows.length > 0) {
    board.drawArrows(arrows);
  } else {
    board.clearArrows();
  }
}

// UI helpers
function hasActiveFilters() {
  const hasTacticalFilter = currentTacticalFilter && currentTacticalFilter !== 'all';
  const hasPhaseFilter = currentPhaseFilters.length > 0 && currentPhaseFilters.length < 3;
  const hasGameTypeFilter = currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4;
  const hasColorFilter = currentColorFilter && currentColorFilter !== 'both';
  const hasDifficultyFilter = currentDifficultyFilters.length > 0 && currentDifficultyFilters.length < 3;
  return hasTacticalFilter || hasPhaseFilter || hasGameTypeFilter || hasColorFilter || hasDifficultyFilter;
}

function updateFilterCountBadge() {
  const badge = document.getElementById('filtersCountBadge');
  if (!badge) return;
  let count = 0;
  if (currentTacticalFilter && currentTacticalFilter !== 'all') count++;
  if (currentPhaseFilters.length > 0 && currentPhaseFilters.length < 3) count++;
  if (currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4) count++;
  if (currentColorFilter && currentColorFilter !== 'both') count++;
  if (currentDifficultyFilters.length > 0 && currentDifficultyFilters.length < 3) count++;
  badge.textContent = count > 0 ? count + ' active' : '0 active';
  badge.style.display = count > 0 ? '' : 'none';
}

function showEmptyState(errorType) {
  trainerLayout.style.display = 'none';
  emptyState.style.display = 'block';
  if (statsCard) statsCard.style.display = 'none';
  if (sessionBar) sessionBar.style.display = 'none';
  emptyStateAction.onclick = null;

  if (errorType === 'no_games') {
    emptyStateTitle.textContent = t('trainer.empty.no_games_title');
    emptyStateMessage.textContent = t('trainer.empty.no_games_message');
    emptyStateAction.textContent = t('trainer.empty.no_games_action');
    emptyStateAction.href = '/management';
  } else if (errorType === 'no_blunders' && hasActiveFilters()) {
    emptyStateTitle.textContent = t('trainer.empty.no_matching_title');
    emptyStateMessage.textContent = t('trainer.empty.no_matching_message');
    emptyStateAction.textContent = t('trainer.empty.no_matching_action');
    emptyStateAction.href = '#';
    emptyStateAction.onclick = (e) => {
      e.preventDefault();
      clearAllFilters();
    };
  } else if (errorType === 'no_blunders') {
    emptyStateTitle.textContent = t('trainer.empty.no_blunders_title');
    emptyStateMessage.textContent = t('trainer.empty.no_blunders_message');
    emptyStateAction.textContent = t('trainer.empty.no_blunders_action');
    emptyStateAction.href = '/management';
  } else {
    emptyStateTitle.textContent = t('trainer.empty.default_title');
    emptyStateMessage.textContent = t('trainer.empty.default_message');
    emptyStateAction.textContent = t('trainer.empty.default_action');
    emptyStateAction.href = '/management';
  }
}

function hideEmptyState() {
  emptyState.style.display = 'none';
  trainerLayout.style.display = 'grid';
  if (statsCard) statsCard.style.display = 'block';
  if (sessionBar) sessionBar.style.display = 'flex';
}

function showBoardResult(accentClass, titleText, detail) {
  boardResultCard.className = 'board-result-card visible ' + accentClass;
  feedbackTitle.textContent = titleText;
  feedbackDetail.textContent = detail;
  movePrompt.style.display = 'none';
}

function hideBoardResult() {
  boardResultCard.classList.remove('visible');
  movePrompt.style.display = '';
  tryBestBtn.style.display = '';
  if (tacticalDetails) tacticalDetails.removeAttribute('open');
  if (explanationDetails) explanationDetails.removeAttribute('open');
}

function toggleBoardResultOverlay() {
  if (boardResultCard.classList.contains('visible')) {
    hideBoardResult();
  } else {
    boardResultCard.classList.add('visible');
    movePrompt.style.display = 'none';
  }
}

function updateColorBadge(color) {
  if (colorBadge) {
    if (color === 'white') {
      colorBadge.className = 'color-badge white';
      colorBadge.innerHTML = '<span class="color-dot white"></span> ' + t('trainer.color.playing_as_white');
    } else {
      colorBadge.className = 'color-badge black';
      colorBadge.innerHTML = '<span class="color-dot black"></span> ' + t('trainer.color.playing_as_black');
    }
  }
  const colorIndicator = document.getElementById('colorIndicator');
  const colorTagText = document.getElementById('colorTagText');
  if (colorIndicator) {
    colorIndicator.className = 'color-indicator ' + (color === 'white' ? 'white-piece' : 'black-piece');
  }
  if (colorTagText) {
    colorTagText.textContent = color === 'white' ? t('chess.color.white') : t('chess.color.black');
  }
}

function updatePhaseBadge(phase) {
  if (!phaseBadge) return;
  if (phase) {
    phaseBadge.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
    phaseBadge.className = 'context-tag phase-highlight';
    phaseBadge.style.display = 'inline-block';
  } else {
    phaseBadge.style.display = 'none';
  }
}

function updateTacticalBadge(pattern) {
  if (!tacticalBadge) return;
  const tacticalSep = document.getElementById('tacticalSeparator');
  if (pattern && pattern !== 'None') {
    tacticalPatternName.textContent = pattern;
    tacticalBadge.style.display = 'inline-flex';
    if (tacticalSep) tacticalSep.style.display = '';
  } else {
    tacticalBadge.style.display = 'none';
    if (tacticalSep) tacticalSep.style.display = 'none';
  }
}

function showTacticalInfo(pattern, reason) {
  if (!tacticalDetails) return;
  if (pattern && pattern !== 'None' && reason) {
    tacticalInfoTitle.textContent = pattern;
    tacticalInfoReason.textContent = reason;
    tacticalDetails.style.display = '';
  } else {
    tacticalDetails.style.display = 'none';
  }
}

function showExplanation(blunderText, bestText) {
  if (!explanationDetails) return;
  if (!blunderText && !bestText) {
    explanationDetails.style.display = 'none';
    return;
  }
  explanationBlunder.textContent = blunderText || '';
  explanationBest.textContent = bestText || '';
  explanationDetails.style.display = '';
}

function updateGameLink(url) {
  const el = document.getElementById('gameLink');
  const sep = document.getElementById('gameLinkSeparator');
  if (!el) return;
  if (url) {
    el.href = url;
    el.style.display = 'inline-flex';
    if (sep) sep.style.display = '';
  } else {
    el.style.display = 'none';
    if (sep) sep.style.display = 'none';
  }
}

function updateCopyDebugBtn(gameId, ply) {
  const btn = document.getElementById('copyDebugBtn');
  if (!btn) return;
  btn.style.display = gameId ? 'inline-block' : 'none';
  btn.onclick = async () => {
    try {
      const params = ply != null ? { ply } : {};
      const text = await client.debug.gameInfo(gameId, params);
      await navigator.clipboard.writeText(text);
      const original = btn.textContent;
      btn.textContent = '✅ ' + t('trainer.debug.copied');
      setTimeout(() => { btn.textContent = original; }, 1500);
    } catch (e) {
      console.error('Copy debug failed:', e);
    }
  };
}

let currentStarred = false;

function updateStarButton(gameId, ply) {
  const btn = document.getElementById('starPuzzleBtn');
  if (!btn) return;
  btn.style.display = gameId ? 'inline-block' : 'none';

  async function refreshState() {
    try {
      const resp = await client.starred.isStarred(gameId, ply);
      currentStarred = resp.starred;
      btn.textContent = currentStarred ? '★ ' + t('trainer.star.remove') : '☆ ' + t('trainer.star.add');
      btn.title = currentStarred ? t('trainer.star.remove') : t('trainer.star.add');
    } catch {
      // Ignore errors
    }
  }

  btn.onclick = async () => {
    try {
      if (currentStarred) {
        await client.starred.unstar(gameId, ply);
        currentStarred = false;
        btn.textContent = '☆ ' + t('trainer.star.add');
        btn.title = t('trainer.star.add');
      } else {
        await client.starred.star(gameId, ply);
        currentStarred = true;
        btn.textContent = '★ ' + t('trainer.star.remove');
        btn.title = t('trainer.star.remove');
      }
    } catch (e) {
      console.error('Star toggle failed:', e);
    }
  };

  refreshState();
}

function getLastMove() {
  const history = game.history({ verbose: true });
  return history.length > 0 ? history[history.length - 1] : null;
}

function updateCurrentMove() {
  const lastMove = getLastMove();
  currentMoveEl.textContent = lastMove ? lastMove.san : '-';
}

function updateMoveHistory() {
  moveHistoryEl.textContent = moveHistory.join(' ');
}

// Board move handler
function onBoardMove(_orig, _dest, move) {
  updateCurrentMove();
  board.clearArrows();
  setTimeout(() => redrawAllHighlights(), 50);
  if (blunderSection) blunderSection.classList.add('blunder-dimmed');

  if (bestRevealed) {
    moveHistory.push(move.san);
    updateMoveHistory();
    historySection.style.display = 'block';
  } else if (!submitted) {
    const uci = move.from + move.to + (move.promotion || '');
    if (puzzle && uci === puzzle.best_move_uci) {
      setTimeout(() => submitMoveAction(), 150);
    } else {
      submitBtn.style.display = '';
    }
  }
}

// Core actions
async function loadPuzzle() {
  updateFilterCountBadge();
  submitted = false;
  bestRevealed = false;
  boardFlipped = false;
  moveHistory = [];
  hideBoardResult();
  if (blunderSection) blunderSection.classList.remove('blunder-dimmed');
  historySection.style.display = 'none';
  moveHistoryEl.textContent = '';
  currentMoveEl.textContent = '-';
  phaseIndicator.textContent = t('trainer.phase.guess');
  phaseIndicator.className = 'phase guess';
  submitBtn.disabled = false;
  submitBtn.style.display = 'none';
  showBestBtn.disabled = false;
  highlightLegend.style.display = 'none';
  legendBest.style.display = 'none';
  legendUser.style.display = 'none';
  legendBlunder.style.display = 'flex';
  if (legendTactic) legendTactic.style.display = 'none';
  updateTacticalBadge(null);
  if (tacticalDetails) tacticalDetails.style.display = 'none';
  if (explanationDetails) explanationDetails.style.display = 'none';

  try {
    const params = {};
    if (currentPhaseFilters.length > 0) params.game_phases = currentPhaseFilters;
    if (currentTacticalFilter && currentTacticalFilter !== 'all') params.tactical_patterns = currentTacticalFilter;
    if (currentGameTypeFilters.length > 0) params.game_types = currentGameTypeFilters;
    if (currentColorFilter && currentColorFilter !== 'both') params.colors = currentColorFilter;
    if (currentDifficultyFilters.length > 0) params.difficulties = currentDifficultyFilters;

    const data = await client.trainer.getPuzzle(params);

    hideEmptyState();
    puzzle = data;
    game = new Chess(puzzle.fen);

    const orientation = puzzle.player_color === 'black' ? 'black' : 'white';

    if (board) board.destroy();

    board = new BoardAdapter('board', {
      fen: puzzle.fen,
      orientation: orientation,
      game: game,
      onMove: onBoardMove
    });

    updateColorBadge(puzzle.player_color);
    updatePhaseBadge(puzzle.game_phase);
    updateTacticalBadge(puzzle.tactical_pattern);
    updateGameLink(puzzle.game_url);
    updateCopyDebugBtn(puzzle.game_id, puzzle.ply);
    updateStarButton(puzzle.game_id, puzzle.ply);
    blunderMove.textContent = puzzle.blunder_san;
    evalBefore.textContent = puzzle.eval_before_display;
    evalAfter.textContent = puzzle.eval_after_display;
    cpLoss.textContent = `(${(puzzle.cp_loss / 100).toFixed(1)})`;

    updateEvalBar(puzzle.eval_before, puzzle.player_color, evalBarFill, evalValue);

    bestMoveDisplay.textContent = puzzle.best_move_san || '...';
    bestLineDisplay.textContent = puzzle.best_line && puzzle.best_line.length > 1 ? puzzle.best_line.slice(1).join(' ') : '';

    setTimeout(() => {
      redrawAllHighlights();
      redrawArrows();
    }, 100);

  } catch (err) {
    if (err instanceof ApiError) {
      const errorMsg = err.message.toLowerCase();
      if (errorMsg.includes('no games found')) {
        showEmptyState('no_games');
      } else if (errorMsg.includes('no blunders found')) {
        showEmptyState('no_blunders');
      } else {
        showEmptyState('unknown');
      }
    } else {
      console.error('Failed to load puzzle:', err);
      showEmptyState('unknown');
    }
  }
}

async function loadSpecificPuzzle(gameId, ply) {
  submitted = false;
  bestRevealed = false;
  boardFlipped = false;
  moveHistory = [];
  hideBoardResult();
  if (blunderSection) blunderSection.classList.remove('blunder-dimmed');
  historySection.style.display = 'none';
  moveHistoryEl.textContent = '';
  currentMoveEl.textContent = '-';
  phaseIndicator.textContent = t('trainer.phase.guess');
  phaseIndicator.className = 'phase guess';
  submitBtn.disabled = false;
  submitBtn.style.display = 'none';
  showBestBtn.disabled = false;
  highlightLegend.style.display = 'none';
  legendBest.style.display = 'none';
  legendUser.style.display = 'none';
  legendBlunder.style.display = 'flex';
  if (legendTactic) legendTactic.style.display = 'none';
  updateTacticalBadge(null);
  if (tacticalDetails) tacticalDetails.style.display = 'none';
  if (explanationDetails) explanationDetails.style.display = 'none';

  try {
    const data = await client.trainer.getSpecificPuzzle(gameId, ply);
    hideEmptyState();
    puzzle = data;
    game = new Chess(puzzle.fen);

    const orientation = puzzle.player_color === 'black' ? 'black' : 'white';
    if (board) board.destroy();
    board = new BoardAdapter('board', {
      fen: puzzle.fen,
      orientation: orientation,
      game: game,
      onMove: onBoardMove,
    });

    updateColorBadge(puzzle.player_color);
    updatePhaseBadge(puzzle.game_phase);
    updateTacticalBadge(puzzle.tactical_pattern);
    updateGameLink(puzzle.game_url);
    updateCopyDebugBtn(puzzle.game_id, puzzle.ply);
    updateStarButton(puzzle.game_id, puzzle.ply);
    blunderMove.textContent = puzzle.blunder_san;
    evalBefore.textContent = puzzle.eval_before_display;
    evalAfter.textContent = puzzle.eval_after_display;
    cpLoss.textContent = `(${(puzzle.cp_loss / 100).toFixed(1)})`;

    updateEvalBar(puzzle.eval_before, puzzle.player_color, evalBarFill, evalValue);
    bestMoveDisplay.textContent = puzzle.best_move_san || '...';
    bestLineDisplay.textContent = puzzle.best_line && puzzle.best_line.length > 1 ? puzzle.best_line.slice(1).join(' ') : '';

    setTimeout(() => {
      redrawAllHighlights();
      redrawArrows();
    }, 100);
  } catch (err) {
    console.error('Failed to load specific puzzle:', err);
    showEmptyState('unknown');
  }
}

async function submitMoveAction() {
  if (!puzzle || !game) return;

  const lastMove = getLastMove();
  if (!lastMove) {
    showBoardResult('accent-revealed', t('common.no_move_made'), t('trainer.feedback.no_move'));
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
    best_move_eval: puzzle.best_move_eval || null
  };

  try {
    const data = await client.trainer.submitMove(payload);

    submitted = true;

    if (data.is_best) {
      showBoardResult('accent-correct', t('trainer.feedback.excellent'), t('trainer.feedback.found_best'));
      tryBestBtn.style.display = 'none';
      phaseIndicator.textContent = t('trainer.phase.correct');
      phaseIndicator.className = 'phase explore';
      legendUser.style.display = 'none';
    } else if (data.is_blunder) {
      showBoardResult('accent-blunder', t('trainer.feedback.same_blunder'), t('trainer.feedback.same_blunder_detail', { userMove: data.user_san }));
      legendUser.style.display = 'none';
    } else {
      const evalDiff = Math.abs(data.user_eval - puzzle.eval_before);
      if (evalDiff < 50) {
        showBoardResult('accent-correct', t('trainer.feedback.good_move'), t('trainer.feedback.good_move_detail', { userMove: data.user_san }));
      } else {
        showBoardResult('accent-revealed', t('trainer.feedback.not_quite'), t('trainer.feedback.not_quite_detail', { userMove: data.user_san, userEval: data.user_eval_display }));
      }
      legendUser.style.display = 'flex';
      redrawAllHighlightsWithUser(data.user_uci);
    }

    legendBest.style.display = 'flex';
    revealBestMove();

    if (!data.is_best && !data.is_blunder) {
      // User highlight already applied above
    } else {
      redrawAllHighlights();
    }

    if (typeof htmx !== 'undefined') {
      htmx.trigger(document.body, 'statsUpdate');
    }

  } catch (err) {
    showBoardResult('accent-revealed', t('trainer.feedback.error'), err.message || t('trainer.feedback.submit_failed'));
    console.error(err);
  }
}

function revealBestMove() {
  bestRevealed = true;
  boardResultCard.classList.add('visible', 'best-revealed');
  movePrompt.style.display = 'none';
  submitBtn.disabled = true;
  submitBtn.style.display = 'none';
  phaseIndicator.textContent = t('trainer.phase.explore');
  phaseIndicator.className = 'phase explore';

  if (!submitted) {
    redrawAllHighlights();
  }

  if (puzzle) {
    showTacticalInfo(puzzle.tactical_pattern, puzzle.tactical_reason);
    showExplanation(puzzle.explanation_blunder, puzzle.explanation_best);
    redrawAllHighlights();
  }

  redrawArrows();
}

function resetPosition() {
  if (!puzzle) return;
  game = new Chess(puzzle.fen);
  board.setPosition(puzzle.fen, game);
  currentMoveEl.textContent = '-';
  moveHistory = [];
  updateMoveHistory();

  if (!bestRevealed) {
    hideBoardResult();
  }

  setTimeout(() => {
    redrawAllHighlights();
    redrawArrows();
  }, 50);
}

function playBestMove() {
  if (!puzzle || !puzzle.best_move_uci) return;

  const wasVisible = boardResultCard.classList.contains('visible');
  if (wasVisible) hideBoardResult();

  const execute = () => {
    game = new Chess(puzzle.fen);
    const from = puzzle.best_move_uci.slice(0, 2);
    const to = puzzle.best_move_uci.slice(2, 4);
    const promotion = puzzle.best_move_uci.length > 4 ? puzzle.best_move_uci[4] : undefined;

    const move = game.move({ from, to, promotion });
    if (move) {
      board.setPosition(game.fen(), game);
      moveHistory = [move.san];
      updateMoveHistory();
      updateCurrentMove();
      historySection.style.display = 'block';
    }
  };

  if (wasVisible) {
    setTimeout(execute, 100);
  } else {
    execute();
  }
}

function undoMove() {
  if (game.history().length === 0) return;
  game.undo();
  board.setPosition(game.fen(), game);
  moveHistory.pop();
  updateMoveHistory();
  updateCurrentMove();
}

function openLichessAnalysis() {
  if (!puzzle) return;
  const fen = game.fen();
  const encodedFen = fen.replace(/ /g, '_');
  const color = puzzle.player_color;

  const arrows = [];
  const atOriginalPosition = game.fen() === puzzle.fen;

  if (atOriginalPosition) {
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      arrows.push(`R${puzzle.blunder_uci.slice(0, 2)}${puzzle.blunder_uci.slice(2, 4)}`);
    }
    if (puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      arrows.push(`G${puzzle.best_move_uci.slice(0, 2)}${puzzle.best_move_uci.slice(2, 4)}`);
    }
  }

  const arrowHash = arrows.length > 0 ? '#' + arrows.join(',') : '';
  const url = `https://lichess.org/analysis/${encodedFen}?color=${color}${arrowHash}`;
  window.open(url, '_blank');
}

function flipBoard() {
  if (!board || !puzzle) return;
  boardFlipped = !boardFlipped;
  const orientation = puzzle.player_color === 'black' ? 'black' : 'white';
  board.setOrientation(boardFlipped ? (orientation === 'white' ? 'black' : 'white') : orientation);
}

function toggleShortcutsOverlay() {
  if (!shortcutsOverlay) return;
  const visible = shortcutsOverlay.classList.contains('visible');
  shortcutsOverlay.classList.toggle('visible', !visible);
}

// Filter persistence
const phaseFilter = new FilterPersistence({
  storageKey: 'blunder-tutor-phase-filters',
  checkboxSelector: '.phase-filter-checkbox',
  defaultValues: []
});

const gameTypeFilter = new FilterPersistence({
  storageKey: 'blunder-tutor-game-type-filters',
  checkboxSelector: '.game-type-checkbox',
  defaultValues: ['bullet', 'blitz', 'rapid']
});

const difficultyFilter = new FilterPersistence({
  storageKey: 'blunder-tutor-difficulty-filters',
  checkboxSelector: '.difficulty-filter-checkbox',
  defaultValues: ['easy', 'medium', 'hard']
});

const COLOR_FILTER_STORAGE_KEY = 'blunder-tutor-color-filter';
const FILTERS_COLLAPSED_KEY = 'blunder-tutor-filters-collapsed';

function clearAllFilters() {
  currentTacticalFilter = 'all';
  localStorage.removeItem('blunder-tutor-tactical-filter');
  tacticalFilterBtns.forEach(btn => {
    btn.classList.toggle('active', btn.dataset.pattern === 'all');
  });

  currentPhaseFilters = phaseFilter.reset(['opening', 'middlegame', 'endgame']);
  currentGameTypeFilters = gameTypeFilter.reset(['bullet', 'blitz', 'rapid']);

  currentColorFilter = 'both';
  localStorage.removeItem(COLOR_FILTER_STORAGE_KEY);
  colorFilterRadios.forEach(radio => {
    radio.checked = radio.value === 'both';
  });

  currentDifficultyFilters = difficultyFilter.reset(['easy', 'medium', 'hard']);

  loadPuzzle();
}

function loadTacticalFilterFromStorage() {
  const stored = localStorage.getItem('blunder-tutor-tactical-filter');
  if (stored) {
    currentTacticalFilter = stored;
    tacticalFilterBtns.forEach(btn => {
      btn.classList.toggle('active', btn.dataset.pattern === stored);
    });
  }
}

function loadColorFilterFromStorage() {
  const stored = localStorage.getItem(COLOR_FILTER_STORAGE_KEY);
  if (stored && (stored === 'white' || stored === 'black')) {
    currentColorFilter = stored;
    colorFilterRadios.forEach(radio => {
      radio.checked = radio.value === stored;
    });
  } else {
    currentColorFilter = 'both';
    colorFilterRadios.forEach(radio => {
      radio.checked = radio.value === 'both';
    });
  }
}

function toggleFiltersPanel() {
  filtersCollapsed = !filtersCollapsed;
  if (filtersCollapsed) {
    filtersContent.classList.add('collapsed');
    filtersChevron.classList.add('collapsed');
  } else {
    filtersContent.classList.remove('collapsed');
    filtersChevron.classList.remove('collapsed');
  }
  localStorage.setItem(FILTERS_COLLAPSED_KEY, JSON.stringify(filtersCollapsed));
}

function loadFiltersPanelState() {
  const stored = localStorage.getItem(FILTERS_COLLAPSED_KEY);
  if (stored) {
    try {
      filtersCollapsed = JSON.parse(stored);
      if (filtersCollapsed) {
        filtersContent.classList.add('collapsed');
        filtersChevron.classList.add('collapsed');
      }
    } catch {
      filtersCollapsed = false;
    }
  }
}

let boardSettingsCollapsed = true;
const BOARD_SETTINGS_COLLAPSED_KEY = 'boardSettingsCollapsed';

function toggleBoardSettingsPanel() {
  boardSettingsCollapsed = !boardSettingsCollapsed;
  if (boardSettingsCollapsed) {
    boardSettingsContent.classList.add('collapsed');
    boardSettingsChevron.classList.add('collapsed');
  } else {
    boardSettingsContent.classList.remove('collapsed');
    boardSettingsChevron.classList.remove('collapsed');
  }
  localStorage.setItem(BOARD_SETTINGS_COLLAPSED_KEY, JSON.stringify(boardSettingsCollapsed));
}

function loadBoardSettingsPanelState() {
  const stored = localStorage.getItem(BOARD_SETTINGS_COLLAPSED_KEY);
  if (stored) {
    try {
      boardSettingsCollapsed = JSON.parse(stored);
      if (!boardSettingsCollapsed) {
        boardSettingsContent.classList.remove('collapsed');
        boardSettingsChevron.classList.remove('collapsed');
      }
    } catch {
      boardSettingsCollapsed = true;
    }
  }
}

// Board visual settings
async function loadBoardSettings() {
  try {
    boardSettings = await client.settings.getBoard();
    applyBoardColors();
    applyPieceSet(boardSettings.piece_set || 'wikipedia');
  } catch (err) {
    console.warn('Failed to load board settings:', err);
  }
}

function applyBoardColors() {
  const root = document.documentElement;
  root.style.setProperty('--board-light', boardSettings.board_light);
  root.style.setProperty('--board-dark', boardSettings.board_dark);
  applyBoardBackground(boardSettings.board_light, boardSettings.board_dark);
}

// Event listeners
submitBtn.addEventListener('click', (e) => { e.stopPropagation(); submitMoveAction(); });
resetBtn.addEventListener('click', resetPosition);
showBestBtn.addEventListener('click', (e) => {
  e.stopPropagation();
  if (bestRevealed) {
    toggleBoardResultOverlay();
  } else {
    showBoardResult('accent-revealed', t('trainer.feedback.best_revealed'), t('trainer.feedback.best_revealed_detail'));
    revealBestMove();
  }
});
nextBtn.addEventListener('click', loadPuzzle);
tryBestBtn.addEventListener('click', playBestMove);
overlayNextBtn.addEventListener('click', (e) => { e.stopPropagation(); loadPuzzle(); });
undoBtn.addEventListener('click', undoMove);
lichessBtn.addEventListener('click', openLichessAnalysis);

if (shortcutsClose) {
  shortcutsClose.addEventListener('click', toggleShortcutsOverlay);
}
if (shortcutsOverlay) {
  shortcutsOverlay.addEventListener('click', (e) => {
    if (e.target === shortcutsOverlay) toggleShortcutsOverlay();
  });
}
if (shortcutsHintBtn) {
  shortcutsHintBtn.addEventListener('click', toggleShortcutsOverlay);
}
document.addEventListener('click', (e) => {
  if (!boardResultCard.classList.contains('visible')) return;
  const inner = boardResultCard.querySelector('.board-result-inner');
  if (inner && !inner.contains(e.target)) {
    hideBoardResult();
  }
});
if (showArrowsCheckbox) {
  showArrowsCheckbox.addEventListener('change', redrawArrows);
}
if (showThreatsCheckbox) {
  showThreatsCheckbox.addEventListener('change', () => redrawAllHighlights());
}
if (showTacticsCheckbox) {
  showTacticsCheckbox.addEventListener('change', () => redrawAllHighlights());
}

phaseFilterCheckboxes.forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    currentPhaseFilters = phaseFilter.save();
    loadPuzzle();
  });
});

tacticalFilterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    tacticalFilterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentTacticalFilter = btn.dataset.pattern;
    localStorage.setItem('blunder-tutor-tactical-filter', currentTacticalFilter);
    loadPuzzle();
  });
});

gameTypeCheckboxes.forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    currentGameTypeFilters = gameTypeFilter.save();
    loadPuzzle();
  });
});

difficultyFilterCheckboxes.forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    currentDifficultyFilters = difficultyFilter.save();
    loadPuzzle();
  });
});

colorFilterRadios.forEach(radio => {
  radio.addEventListener('change', () => {
    colorFilterRadios.forEach(r => {
      if (r.checked) currentColorFilter = r.value;
    });
    if (currentColorFilter === 'both') {
      localStorage.removeItem(COLOR_FILTER_STORAGE_KEY);
    } else {
      localStorage.setItem(COLOR_FILTER_STORAGE_KEY, currentColorFilter);
    }
    loadPuzzle();
  });
});

if (filtersHeader) filtersHeader.addEventListener('click', toggleFiltersPanel);
if (filtersToggleBtn) {
  filtersToggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleFiltersPanel();
  });
}
if (boardSettingsHeader) boardSettingsHeader.addEventListener('click', toggleBoardSettingsPanel);
if (document.getElementById('boardSettingsToggleBtn')) {
  document.getElementById('boardSettingsToggleBtn').addEventListener('click', (e) => {
    e.stopPropagation();
    toggleBoardSettingsPanel();
  });
}

document.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

  if (e.key === 'Escape') {
    if (shortcutsOverlay && shortcutsOverlay.classList.contains('visible')) {
      toggleShortcutsOverlay();
      return;
    }
    if (boardResultCard.classList.contains('visible')) {
      hideBoardResult();
    }
    return;
  }

  if (e.key === '?') { toggleShortcutsOverlay(); return; }

  if (e.key === 'Enter' && !submitted) {
    e.preventDefault();
    submitMoveAction();
  } else if (e.key === 'n' || e.key === 'N') {
    loadPuzzle();
  } else if (e.key === 'r' || e.key === 'R') {
    resetPosition();
  } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    undoMove();
  } else if (e.key === 'f' || e.key === 'F') {
    flipBoard();
  } else if (e.key === 'b' || e.key === 'B') {
    if (bestRevealed) {
      toggleBoardResultOverlay();
    } else {
      showBoardResult('accent-revealed', t('trainer.feedback.best_revealed'), t('trainer.feedback.best_revealed_detail'));
      revealBestMove();
    }
  } else if (e.key === 'p' || e.key === 'P') {
    playBestMove();
  } else if (e.key === 'a' || e.key === 'A') {
    if (showArrowsCheckbox) {
      showArrowsCheckbox.checked = !showArrowsCheckbox.checked;
      showArrowsCheckbox.dispatchEvent(new Event('change'));
    }
  } else if (e.key === 't' || e.key === 'T') {
    if (showThreatsCheckbox) {
      showThreatsCheckbox.checked = !showThreatsCheckbox.checked;
      showThreatsCheckbox.dispatchEvent(new Event('change'));
    }
  } else if (e.key === 'l' || e.key === 'L') {
    openLichessAnalysis();
  }
});

// Initialize
async function init() {
  currentPhaseFilters = phaseFilter.load();
  loadTacticalFilterFromStorage();
  currentGameTypeFilters = gameTypeFilter.load();
  currentDifficultyFilters = difficultyFilter.load();
  loadColorFilterFromStorage();
  loadFiltersPanelState();
  loadBoardSettingsPanelState();
  updateFilterCountBadge();

  await loadBoardSettings();

  const urlParams = new URLSearchParams(window.location.search);
  const deepGameId = urlParams.get('game_id');
  const deepPly = urlParams.get('ply');

  if (deepGameId && deepPly) {
    await loadSpecificPuzzle(deepGameId, parseInt(deepPly, 10));
  } else {
    loadPuzzle();
  }
}

init();

// WebSocket
wsClient.connect();
wsClient.subscribe(['stats.updated']);

wsClient.on('stats.updated', () => {
  htmx.trigger('#statsContent', 'statsUpdate');
});
