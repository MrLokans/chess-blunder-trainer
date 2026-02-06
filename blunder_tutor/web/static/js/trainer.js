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
let filtersCollapsed = false;
let boardFlipped = false;

let boardSettings = {
  piece_set: 'wikipedia',
  board_light: '#f0d9b5',
  board_dark: '#b58863'
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
const feedback = document.getElementById('feedback');
const feedbackTitle = document.getElementById('feedbackTitle');
const feedbackDetail = document.getElementById('feedbackDetail');
const currentMoveEl = document.getElementById('currentMove');
const bestMoveInfo = document.getElementById('bestMoveInfo');
const bestMoveDisplay = document.getElementById('bestMoveDisplay');
const bestLineDisplay = document.getElementById('bestLineDisplay');
const historySection = document.getElementById('historySection');
const moveHistoryEl = document.getElementById('moveHistory');

const submitBtn = document.getElementById('submitBtn');
const resetBtn = document.getElementById('resetBtn');
const showBestBtn = document.getElementById('showBestBtn');
const nextBtn = document.getElementById('nextBtn');
const tryBestBtn = document.getElementById('tryBestBtn');
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
const tacticalInfo = document.getElementById('tacticalInfo');
const tacticalInfoTitle = document.getElementById('tacticalInfoTitle');
const tacticalInfoReason = document.getElementById('tacticalInfoReason');
const tacticalFilterBtns = document.querySelectorAll('.tactical-filter-btn');
const showTacticsCheckbox = document.getElementById('showTactics');
const legendTactic = document.getElementById('legendTactic');
const gameTypeCheckboxes = document.querySelectorAll('.game-type-checkbox');
const colorFilterRadios = document.querySelectorAll('input[name="colorFilter"]');
const filtersHeader = document.getElementById('filtersHeader');
const filtersToggleBtn = document.getElementById('filtersToggleBtn');
const filtersContent = document.getElementById('filtersContent');
const filtersChevron = document.getElementById('filtersChevron');
const emptyState = document.getElementById('emptyState');
const trainerLayout = document.getElementById('trainerLayout');
const emptyStateTitle = document.getElementById('emptyStateTitle');
const emptyStateMessage = document.getElementById('emptyStateMessage');
const emptyStateAction = document.getElementById('emptyStateAction');
const statsCard = document.getElementById('statsCard');
const shortcutsOverlay = document.getElementById('shortcutsOverlay');
const shortcutsClose = document.getElementById('shortcutsClose');
const shortcutsHintBtn = document.getElementById('shortcutsHintBtn');

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
  const threats = buildThreatHighlights(game, showThreatsCheckbox.checked);
  const tactical = buildTacticalHighlights(puzzle, game, bestRevealed,
    showTacticsCheckbox && showTacticsCheckbox.checked);

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
  const threats = buildThreatHighlights(game, showThreatsCheckbox.checked);
  const tactical = buildTacticalHighlights(puzzle, game, bestRevealed,
    showTacticsCheckbox && showTacticsCheckbox.checked);

  if (bestRevealed && tactical.size > 0 && legendTactic) {
    legendTactic.style.display = 'flex';
  }

  const merged = mergeHighlights(blunder, best, user, threats, tactical);
  board.setCustomHighlight(merged.size > 0 ? merged : undefined);
}

function redrawArrows() {
  if (!board || !puzzle) return;
  if (!showArrowsCheckbox.checked) {
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
  return hasTacticalFilter || hasPhaseFilter || hasGameTypeFilter || hasColorFilter;
}

function showEmptyState(errorType) {
  trainerLayout.style.display = 'none';
  emptyState.style.display = 'block';
  statsCard.style.display = 'none';
  emptyStateAction.onclick = null;

  if (errorType === 'no_games') {
    emptyStateTitle.textContent = 'No games imported';
    emptyStateMessage.textContent = 'Import your games from Lichess or Chess.com to start training on your blunders.';
    emptyStateAction.textContent = 'Import Games';
    emptyStateAction.href = '/management';
  } else if (errorType === 'no_blunders' && hasActiveFilters()) {
    emptyStateTitle.textContent = 'No matching blunders';
    emptyStateMessage.textContent = 'No blunders found with the current filters. Try selecting different filters or clear them to see all blunders.';
    emptyStateAction.textContent = 'Clear Filters';
    emptyStateAction.href = '#';
    emptyStateAction.onclick = (e) => {
      e.preventDefault();
      clearAllFilters();
    };
  } else if (errorType === 'no_blunders') {
    emptyStateTitle.textContent = 'No blunders found';
    emptyStateMessage.textContent = 'Your games have been imported but no blunders were found yet. Run analysis to identify blunders in your games.';
    emptyStateAction.textContent = 'Run Analysis';
    emptyStateAction.href = '/management';
  } else {
    emptyStateTitle.textContent = 'No puzzles available';
    emptyStateMessage.textContent = 'Import your games to start training on your blunders.';
    emptyStateAction.textContent = 'Import Games';
    emptyStateAction.href = '/management';
  }
}

function hideEmptyState() {
  emptyState.style.display = 'none';
  trainerLayout.style.display = 'grid';
  statsCard.style.display = 'block';
}

function showFeedback(type, title, detail) {
  feedback.className = 'feedback visible ' + type;
  feedbackTitle.textContent = title;
  feedbackDetail.textContent = detail;
}

function hideFeedback() {
  feedback.className = 'feedback';
}

function updateColorBadge(color) {
  if (color === 'white') {
    colorBadge.className = 'color-badge white';
    colorBadge.innerHTML = '<span class="color-dot white"></span> Playing as White';
  } else {
    colorBadge.className = 'color-badge black';
    colorBadge.innerHTML = '<span class="color-dot black"></span> Playing as Black';
  }
}

function updatePhaseBadge(phase) {
  if (!phaseBadge) return;
  if (phase) {
    phaseBadge.textContent = phase.charAt(0).toUpperCase() + phase.slice(1);
    phaseBadge.className = 'phase-badge ' + phase;
    phaseBadge.style.display = 'inline-block';
  } else {
    phaseBadge.style.display = 'none';
  }
}

function updateTacticalBadge(pattern) {
  if (!tacticalBadge) return;
  if (pattern && pattern !== 'None') {
    tacticalPatternName.textContent = pattern;
    tacticalBadge.style.display = 'inline-flex';
  } else {
    tacticalBadge.style.display = 'none';
  }
}

function showTacticalInfo(pattern, reason) {
  if (!tacticalInfo) return;
  if (pattern && pattern !== 'None' && reason) {
    tacticalInfoTitle.textContent = pattern;
    tacticalInfoReason.textContent = reason;
    tacticalInfo.style.display = 'block';
  } else {
    tacticalInfo.style.display = 'none';
  }
}

function updateGameLink(url) {
  const el = document.getElementById('gameLink');
  if (!el) return;
  if (url) {
    el.href = url;
    el.style.display = 'inline';
  } else {
    el.style.display = 'none';
  }
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

  if (bestRevealed) {
    moveHistory.push(move.san);
    updateMoveHistory();
    historySection.style.display = 'block';
  }
}

// Core actions
async function loadPuzzle() {
  submitted = false;
  bestRevealed = false;
  boardFlipped = false;
  moveHistory = [];
  hideFeedback();
  bestMoveInfo.classList.remove('visible');
  historySection.style.display = 'none';
  moveHistoryEl.textContent = '';
  currentMoveEl.textContent = '-';
  phaseIndicator.textContent = 'Find the best move';
  phaseIndicator.className = 'phase guess';
  submitBtn.disabled = false;
  showBestBtn.disabled = false;
  highlightLegend.style.display = 'none';
  legendBest.style.display = 'none';
  legendUser.style.display = 'none';
  legendBlunder.style.display = 'flex';
  if (legendTactic) legendTactic.style.display = 'none';
  updateTacticalBadge(null);
  if (tacticalInfo) tacticalInfo.style.display = 'none';

  try {
    const params = {};
    if (currentPhaseFilters.length > 0) params.game_phases = currentPhaseFilters;
    if (currentTacticalFilter && currentTacticalFilter !== 'all') params.tactical_patterns = currentTacticalFilter;
    if (currentGameTypeFilters.length > 0) params.game_types = currentGameTypeFilters;
    if (currentColorFilter && currentColorFilter !== 'both') params.colors = currentColorFilter;

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
    blunderMove.textContent = puzzle.blunder_san;
    evalBefore.textContent = puzzle.eval_before_display;
    evalAfter.textContent = puzzle.eval_after_display;
    cpLoss.textContent = (puzzle.cp_loss / 100).toFixed(1) + ' pawns';

    updateEvalBar(puzzle.eval_before, puzzle.player_color, evalBarFill, evalValue);

    bestMoveDisplay.textContent = puzzle.best_move_san || '...';
    bestLineDisplay.textContent = puzzle.best_line ? puzzle.best_line.join(' ') : '...';

    setTimeout(() => {
      highlightLegend.style.display = 'flex';
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
      } else if (errorMsg.includes('no username configured')) {
        window.location.href = '/setup';
      } else {
        showEmptyState('unknown');
      }
    } else {
      console.error('Failed to load puzzle:', err);
      showEmptyState('unknown');
    }
  }
}

async function submitMoveAction() {
  if (!puzzle || !game) return;

  const lastMove = getLastMove();
  if (!lastMove) {
    showFeedback('incorrect', 'No move made', 'Drag a piece to make a move first.');
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
    username: puzzle.username || '',
    eval_after: puzzle.eval_after || 0,
    best_move_eval: puzzle.best_move_eval || null
  };

  try {
    const data = await client.trainer.submitMove(payload);

    submitted = true;

    if (data.is_best) {
      showFeedback('correct', 'Excellent!', 'You found the best move: ' + data.user_san);
      phaseIndicator.textContent = 'Correct!';
      phaseIndicator.className = 'phase explore';
      legendUser.style.display = 'none';
    } else if (data.is_blunder) {
      showFeedback('blunder-repeat', 'Same blunder!', 'You played the same blunder again: ' + data.user_san + '. The best move was ' + data.best_san);
      legendUser.style.display = 'none';
    } else {
      const evalDiff = Math.abs(data.user_eval - puzzle.eval_before);
      if (evalDiff < 50) {
        showFeedback('correct', 'Good move!', 'Your move ' + data.user_san + ' is solid. Best was ' + data.best_san);
      } else {
        showFeedback('incorrect', 'Not quite', 'Your move: ' + data.user_san + ' (' + data.user_eval_display + '). Best was ' + data.best_san);
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
    showFeedback('incorrect', 'Error', err.message || 'Failed to submit move');
    console.error(err);
  }
}

function revealBestMove() {
  bestRevealed = true;
  bestMoveInfo.classList.add('visible');
  submitBtn.disabled = true;
  showBestBtn.disabled = true;
  phaseIndicator.textContent = 'Explore the position';
  phaseIndicator.className = 'phase explore';

  if (!submitted) {
    redrawAllHighlights();
  }

  if (puzzle) {
    showTacticalInfo(puzzle.tactical_pattern, puzzle.tactical_reason);
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
    hideFeedback();
  }

  setTimeout(() => {
    redrawAllHighlights();
    redrawArrows();
  }, 50);
}

function playBestMove() {
  if (!puzzle || !puzzle.best_move_uci) return;

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

// Board settings
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
submitBtn.addEventListener('click', submitMoveAction);
resetBtn.addEventListener('click', resetPosition);
showBestBtn.addEventListener('click', () => {
  revealBestMove();
  showFeedback('incorrect', 'Best move revealed', 'The best move was ' + puzzle.best_move_san);
});
nextBtn.addEventListener('click', loadPuzzle);
tryBestBtn.addEventListener('click', playBestMove);
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
showArrowsCheckbox.addEventListener('change', redrawArrows);
showThreatsCheckbox.addEventListener('change', () => redrawAllHighlights());
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

document.addEventListener('keydown', (e) => {
  const tag = (e.target.tagName || '').toLowerCase();
  if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

  if (e.key === 'Escape') {
    if (shortcutsOverlay && shortcutsOverlay.classList.contains('visible')) {
      toggleShortcutsOverlay();
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
    if (!bestRevealed) {
      revealBestMove();
      showFeedback('incorrect', 'Best move revealed', 'The best move was ' + puzzle.best_move_san);
    }
  } else if (e.key === 'p' || e.key === 'P') {
    playBestMove();
  } else if (e.key === 'a' || e.key === 'A') {
    showArrowsCheckbox.checked = !showArrowsCheckbox.checked;
    showArrowsCheckbox.dispatchEvent(new Event('change'));
  } else if (e.key === 't' || e.key === 'T') {
    showThreatsCheckbox.checked = !showThreatsCheckbox.checked;
    showThreatsCheckbox.dispatchEvent(new Event('change'));
  } else if (e.key === 'l' || e.key === 'L') {
    openLichessAnalysis();
  }
});

// Initialize
async function init() {
  currentPhaseFilters = phaseFilter.load();
  loadTacticalFilterFromStorage();
  currentGameTypeFilters = gameTypeFilter.load();
  loadColorFilterFromStorage();
  loadFiltersPanelState();

  await loadBoardSettings();
  loadPuzzle();
}

init();

// WebSocket
wsClient.connect();
wsClient.subscribe(['stats.updated']);

wsClient.on('stats.updated', () => {
  htmx.trigger('#statsContent', 'statsUpdate');
});
