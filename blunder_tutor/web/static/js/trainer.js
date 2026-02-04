// Trainer application JavaScript

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
const currentMove = document.getElementById('currentMove');
const bestMoveInfo = document.getElementById('bestMoveInfo');
const bestMoveDisplay = document.getElementById('bestMoveDisplay');
const bestLineDisplay = document.getElementById('bestLineDisplay');
const historySection = document.getElementById('historySection');
const moveHistoryEl = document.getElementById('moveHistory');

// Buttons
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
const arrowOverlay = document.getElementById('arrowOverlay');
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

// New filter elements
const gameTypeCheckboxes = document.querySelectorAll('.game-type-checkbox');
const colorFilterRadios = document.querySelectorAll('input[name="colorFilter"]');
const filtersHeader = document.getElementById('filtersHeader');
const filtersToggleBtn = document.getElementById('filtersToggleBtn');
const filtersContent = document.getElementById('filtersContent');
const filtersChevron = document.getElementById('filtersChevron');

// Empty state elements
const emptyState = document.getElementById('emptyState');
const trainerLayout = document.getElementById('trainerLayout');
const emptyStateTitle = document.getElementById('emptyStateTitle');
const emptyStateMessage = document.getElementById('emptyStateMessage');
const emptyStateAction = document.getElementById('emptyStateAction');
const statsCard = document.getElementById('statsCard');

// Arrow drawing functions
function getSquareCenter(square, boardEl, orientation) {
  const files = 'abcdefgh';
  const file = files.indexOf(square[0]);
  const rank = parseInt(square[1]) - 1;

  const boardRect = boardEl.getBoundingClientRect();
  const squareSize = boardRect.width / 8;

  let x, y;
  if (orientation === 'white') {
    x = (file + 0.5) * squareSize;
    y = (7 - rank + 0.5) * squareSize;
  } else {
    x = (7 - file + 0.5) * squareSize;
    y = (rank + 0.5) * squareSize;
  }

  return { x, y };
}

function createArrowSVG(arrows, boardEl, orientation) {
  const boardRect = boardEl.getBoundingClientRect();
  const width = boardRect.width;
  const height = boardRect.height;

  let svg = `<svg viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">`;

  // Define arrow markers
  svg += `
    <defs>
      <marker id="arrowhead-red" markerWidth="4" markerHeight="4" refX="2.5" refY="2" orient="auto">
        <polygon points="0 0, 4 2, 0 4" fill="rgba(220, 53, 69, 0.9)" />
      </marker>
      <marker id="arrowhead-green" markerWidth="4" markerHeight="4" refX="2.5" refY="2" orient="auto">
        <polygon points="0 0, 4 2, 0 4" fill="rgba(25, 135, 84, 0.9)" />
      </marker>
      <marker id="arrowhead-orange" markerWidth="4" markerHeight="4" refX="2.5" refY="2" orient="auto">
        <polygon points="0 0, 4 2, 0 4" fill="rgba(253, 126, 20, 0.9)" />
      </marker>
    </defs>
  `;

  for (const arrow of arrows) {
    const from = getSquareCenter(arrow.from, boardEl, orientation);
    const to = getSquareCenter(arrow.to, boardEl, orientation);

    // Shorten the arrow slightly so it doesn't overlap the arrowhead
    const dx = to.x - from.x;
    const dy = to.y - from.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    const shortenBy = 8;
    const toX = to.x - (dx / len) * shortenBy;
    const toY = to.y - (dy / len) * shortenBy;
    const fromX = from.x + (dx / len) * (shortenBy / 2);
    const fromY = from.y + (dy / len) * (shortenBy / 2);

    const color = arrow.color || 'green';
    const strokeColor = color === 'red' ? 'rgba(220, 53, 69, 0.9)' :
                        color === 'orange' ? 'rgba(253, 126, 20, 0.9)' :
                        'rgba(25, 135, 84, 0.9)';
    const markerId = `arrowhead-${color}`;

    svg += `<line x1="${fromX}" y1="${fromY}" x2="${toX}" y2="${toY}"
             stroke="${strokeColor}" stroke-width="8" stroke-linecap="round"
             marker-end="url(#${markerId})" opacity="0.85" />`;
  }

  svg += '</svg>';
  return svg;
}

function drawArrows() {
  if (!showArrowsCheckbox.checked || !puzzle) {
    arrowOverlay.innerHTML = '';
    return;
  }

  const boardEl = document.getElementById('board');
  const orientation = puzzle.player_color === 'black' ? 'black' : 'white';
  const arrows = [];

  // Only draw arrows at original position
  const atOriginalPosition = game.fen() === puzzle.fen;

  if (atOriginalPosition) {
    // Red arrow for blunder
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      arrows.push({
        from: puzzle.blunder_uci.slice(0, 2),
        to: puzzle.blunder_uci.slice(2, 4),
        color: 'red'
      });
    }

    // Green arrow for best move (only after revealed)
    if (bestRevealed && puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      arrows.push({
        from: puzzle.best_move_uci.slice(0, 2),
        to: puzzle.best_move_uci.slice(2, 4),
        color: 'green'
      });
    }
  }

  if (arrows.length > 0) {
    arrowOverlay.innerHTML = createArrowSVG(arrows, boardEl, orientation);
  } else {
    arrowOverlay.innerHTML = '';
  }
}

function clearArrows() {
  arrowOverlay.innerHTML = '';
}

// Threat detection functions
function hasActiveFilters() {
  const hasTacticalFilter = currentTacticalFilter && currentTacticalFilter !== 'all';
  const hasPhaseFilter = currentPhaseFilters.length > 0 && currentPhaseFilters.length < 3;
  const hasGameTypeFilter = currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4;
  const hasColorFilter = currentColorFilter && currentColorFilter !== 'both';
  return hasTacticalFilter || hasPhaseFilter || hasGameTypeFilter || hasColorFilter;
}

function showEmptyState(errorType) {
  // Hide trainer layout, show empty state
  trainerLayout.style.display = 'none';
  emptyState.style.display = 'block';
  statsCard.style.display = 'none';

  // Reset onclick handler
  emptyStateAction.onclick = null;

  if (errorType === 'no_games') {
    emptyStateTitle.textContent = 'No games imported';
    emptyStateMessage.textContent = 'Import your games from Lichess or Chess.com to start training on your blunders.';
    emptyStateAction.textContent = 'Import Games';
    emptyStateAction.href = '/management';
  } else if (errorType === 'no_blunders' && hasActiveFilters()) {
    // No blunders with current filters - offer to clear
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

function clearAllFilters() {
  // Reset tactical filter
  currentTacticalFilter = 'all';
  localStorage.removeItem('blunder-tutor-tactical-filter');
  tacticalFilterBtns.forEach(btn => {
    if (btn.dataset.pattern === 'all') {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });

  // Reset phase filters to all checked
  currentPhaseFilters = ['opening', 'middlegame', 'endgame'];
  localStorage.setItem('blunder-tutor-phase-filters', JSON.stringify(currentPhaseFilters));
  phaseFilterCheckboxes.forEach(checkbox => {
    checkbox.checked = true;
  });

  // Reset game type filters to default selection
  currentGameTypeFilters = ['bullet', 'blitz', 'rapid'];
  localStorage.setItem('blunder-tutor-game-type-filters', JSON.stringify(currentGameTypeFilters));
  gameTypeCheckboxes.forEach(checkbox => {
    checkbox.checked = currentGameTypeFilters.includes(checkbox.value);
  });

  // Reset color filter to both
  currentColorFilter = 'both';
  localStorage.removeItem('blunder-tutor-color-filter');
  colorFilterRadios.forEach(radio => {
    radio.checked = radio.value === 'both';
  });

  // Reload puzzle
  loadPuzzle();
}

function hideEmptyState() {
  emptyState.style.display = 'none';
  trainerLayout.style.display = 'grid';
  statsCard.style.display = 'block';
}

function clearThreatHighlights() {
  document.querySelectorAll('.highlight-hanging, .highlight-pinned, .highlight-checking, .highlight-king-danger').forEach(el => {
    el.classList.remove('highlight-hanging', 'highlight-pinned', 'highlight-checking', 'highlight-king-danger');
  });
}

function clearTacticalHighlights() {
  document.querySelectorAll('.highlight-tactic-primary, .highlight-tactic-secondary').forEach(el => {
    el.classList.remove('highlight-tactic-primary', 'highlight-tactic-secondary');
  });
}

function drawTacticalHighlights() {
  clearTacticalHighlights();

  if (!showTacticsCheckbox || !showTacticsCheckbox.checked) {
    return;
  }

  if (!bestRevealed || !puzzle || !puzzle.tactical_squares) {
    return;
  }

  // Only show at original position
  const atOriginalPosition = game.fen() === puzzle.fen;
  if (!atOriginalPosition) {
    return;
  }

  const squares = puzzle.tactical_squares;
  if (squares.length > 0) {
    // First square is the attacking piece (primary)
    highlightSquare(squares[0], 'highlight-tactic-primary');

    // Rest are target squares (secondary)
    for (let i = 1; i < squares.length; i++) {
      highlightSquare(squares[i], 'highlight-tactic-secondary');
    }

    // Show legend
    if (legendTactic) {
      legendTactic.style.display = 'flex';
    }
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

function getAttackers(gameObj, square, byColor) {
  // Get all pieces of byColor that attack the square
  const attackers = [];
  const dominated_game = new Chess(gameObj.fen());

  // Check all squares for pieces of the attacking color
  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const piece = dominated_game.get(sq);
      if (piece && piece.color === byColor) {
        // Check if this piece can move to the target square
        const moves = dominated_game.moves({ square: sq, verbose: true });
        for (const move of moves) {
          if (move.to === square) {
            attackers.push({ square: sq, piece: piece });
            break;
          }
        }
      }
    }
  }
  return attackers;
}

function getDefenders(gameObj, square, piece) {
  // Count how many pieces of the same color defend this square
  // We do this by temporarily removing the piece and checking attacks
  const dominated_game = new Chess(gameObj.fen());
  const defenderColor = piece.color;

  // Remove the piece temporarily
  dominated_game.remove(square);

  // Now check if any friendly piece can move to this square
  const defenders = [];
  const files = 'abcdefgh';
  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const p = dominated_game.get(sq);
      if (p && p.color === defenderColor) {
        const moves = dominated_game.moves({ square: sq, verbose: true });
        for (const move of moves) {
          if (move.to === square) {
            defenders.push({ square: sq, piece: p });
            break;
          }
        }
      }
    }
  }
  return defenders;
}

function findHangingPieces(gameObj) {
  // Find pieces that are attacked but not defended (or under-defended)
  const hanging = [];
  const files = 'abcdefgh';
  const turnColor = gameObj.turn(); // 'w' or 'b'
  const opponentColor = turnColor === 'w' ? 'b' : 'w';

  for (let f = 0; f < 8; f++) {
    for (let r = 1; r <= 8; r++) {
      const sq = files[f] + r;
      const piece = gameObj.get(sq);
      if (piece && piece.type !== 'k') { // Don't mark kings as hanging
        const attackers = getAttackers(gameObj, sq, piece.color === 'w' ? 'b' : 'w');
        if (attackers.length > 0) {
          const defenders = getDefenders(gameObj, sq, piece);
          if (defenders.length === 0) {
            // Completely undefended and attacked
            hanging.push(sq);
          }
        }
      }
    }
  }
  return hanging;
}

function findKingInCheck(gameObj) {
  // Find if the king to move is in check
  if (gameObj.in_check()) {
    const turnColor = gameObj.turn();
    const files = 'abcdefgh';
    for (let f = 0; f < 8; f++) {
      for (let r = 1; r <= 8; r++) {
        const sq = files[f] + r;
        const piece = gameObj.get(sq);
        if (piece && piece.type === 'k' && piece.color === turnColor) {
          return sq;
        }
      }
    }
  }
  return null;
}

function findCheckableKing(gameObj) {
  // Find if there's a check available for the side to move
  const moves = gameObj.moves({ verbose: true });
  for (const move of moves) {
    // Make the move temporarily
    const testGame = new Chess(gameObj.fen());
    testGame.move(move);
    if (testGame.in_check()) {
      // The opponent's king can be checked - find where it is
      const oppColor = gameObj.turn() === 'w' ? 'b' : 'w';
      const files = 'abcdefgh';
      for (let f = 0; f < 8; f++) {
        for (let r = 1; r <= 8; r++) {
          const sq = files[f] + r;
          const piece = testGame.get(sq);
          if (piece && piece.type === 'k' && piece.color === oppColor) {
            return sq;
          }
        }
      }
    }
  }
  return null;
}

function drawThreatHighlights() {
  clearThreatHighlights();

  if (!showThreatsCheckbox.checked || !game) {
    return;
  }

  // Find hanging pieces
  const hanging = findHangingPieces(game);
  for (const sq of hanging) {
    highlightSquare(sq, 'highlight-hanging');
  }

  // Find king in check
  const kingInCheck = findKingInCheck(game);
  if (kingInCheck) {
    highlightSquare(kingInCheck, 'highlight-king-danger');
  }

  // Find checkable king (opponent's king that can be put in check)
  const checkableKing = findCheckableKing(game);
  if (checkableKing && checkableKing !== kingInCheck) {
    highlightSquare(checkableKing, 'highlight-checking');
  }
}

// Helper functions
function clearHighlights() {
  document.querySelectorAll('.highlight-blunder-from, .highlight-blunder-to, .highlight-best-from, .highlight-best-to, .highlight-user-from, .highlight-user-to').forEach(el => {
    el.classList.remove('highlight-blunder-from', 'highlight-blunder-to', 'highlight-best-from', 'highlight-best-to', 'highlight-user-from', 'highlight-user-to');
  });
}

function clearLegalMoveHighlights() {
  document.querySelectorAll('.highlight-legal-move, .highlight-legal-capture').forEach(el => {
    el.classList.remove('highlight-legal-move', 'highlight-legal-capture');
  });
}

function highlightLegalMoves(square) {
  if (!game) return;

  const moves = game.moves({ square: square, verbose: true });
  for (const move of moves) {
    const targetPiece = game.get(move.to);
    if (targetPiece) {
      highlightSquare(move.to, 'highlight-legal-capture');
    } else {
      highlightSquare(move.to, 'highlight-legal-move');
    }
  }
}

function highlightSquare(square, className) {
  const squareEl = document.querySelector(`.square-${square}`);
  if (squareEl) {
    squareEl.classList.add(className);
  }
}

function highlightMove(uci, type) {
  if (!uci || uci.length < 4) return;
  const from = uci.slice(0, 2);
  const to = uci.slice(2, 4);
  highlightSquare(from, `highlight-${type}-from`);
  highlightSquare(to, `highlight-${type}-to`);
}

function showBlunderHighlight() {
  if (!puzzle || !puzzle.blunder_uci) return;
  highlightMove(puzzle.blunder_uci, 'blunder');
}

function showBestMoveHighlight() {
  if (!puzzle || !puzzle.best_move_uci) return;
  highlightMove(puzzle.best_move_uci, 'best');
}

function showUserMoveHighlight(uci) {
  if (!uci) return;
  highlightMove(uci, 'user');
}

function updateEvalBar(cp, playerColor) {
  // Convert to player perspective
  const playerCp = playerColor === 'black' ? -cp : cp;

  // Map to percentage (sigmoid-like mapping)
  const maxCp = 500;
  const normalized = Math.max(-maxCp, Math.min(maxCp, playerCp));
  const percentage = 50 + (normalized / maxCp) * 50;

  evalBarFill.style.width = percentage + '%';

  // Update value display
  let displayVal;
  if (Math.abs(cp) >= 10000) {
    displayVal = cp > 0 ? '+M' : '-M';
  } else {
    displayVal = (cp >= 0 ? '+' : '') + (cp / 100).toFixed(1);
  }
  evalValue.textContent = displayVal;
  evalValue.className = 'eval-value ' + (playerCp >= 0 ? 'positive' : 'negative');
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
  const dot = colorBadge.querySelector('.color-dot');
  if (color === 'white') {
    colorBadge.className = 'color-badge white';
    dot.className = 'color-dot white';
    colorBadge.innerHTML = '<span class="color-dot white"></span> Playing as White';
  } else {
    colorBadge.className = 'color-badge black';
    dot.className = 'color-dot black';
    colorBadge.innerHTML = '<span class="color-dot black"></span> Playing as Black';
  }
}

function getLastMove() {
  const history = game.history({ verbose: true });
  return history.length > 0 ? history[history.length - 1] : null;
}

function updateCurrentMove() {
  const lastMove = getLastMove();
  if (lastMove) {
    currentMove.textContent = lastMove.san;
  } else {
    currentMove.textContent = '-';
  }
}

function updateMoveHistory() {
  moveHistoryEl.textContent = moveHistory.join(' ');
}

// Board event handlers
function onDragStart(source, piece) {
  // Only allow moves for the player's color
  if (puzzle && puzzle.player_color === 'white' && piece.search(/^b/) !== -1) return false;
  if (puzzle && puzzle.player_color === 'black' && piece.search(/^w/) !== -1) return false;

  // Highlight legal moves for this piece
  highlightLegalMoves(source);
  return true;
}

function onDrop(source, target) {
  // Clear legal move highlights
  clearLegalMoveHighlights();

  const move = game.move({
    from: source,
    to: target,
    promotion: 'q'
  });

  if (move === null) return 'snapback';

  updateCurrentMove();

  // Clear arrows when position changes
  clearArrows();

  // Redraw threat highlights for new position
  setTimeout(() => drawThreatHighlights(), 50);

  // If in exploration mode, record the move
  if (bestRevealed) {
    moveHistory.push(move.san);
    updateMoveHistory();
    historySection.style.display = 'block';
  }
}

function onSnapEnd() {
  board.position(game.fen());
}

// API calls
async function loadPuzzle() {
  // Reset state
  submitted = false;
  bestRevealed = false;
  moveHistory = [];
  hideFeedback();
  bestMoveInfo.classList.remove('visible');
  historySection.style.display = 'none';
  moveHistoryEl.textContent = '';
  currentMove.textContent = '-';
  phaseIndicator.textContent = 'Find the best move';
  phaseIndicator.className = 'phase guess';
  submitBtn.disabled = false;
  showBestBtn.disabled = false;
  clearHighlights();
  clearTacticalHighlights();
  highlightLegend.style.display = 'none';
  legendBest.style.display = 'none';
  legendUser.style.display = 'none';
  legendBlunder.style.display = 'flex';
  if (legendTactic) legendTactic.style.display = 'none';
  updateTacticalBadge(null);
  if (tacticalInfo) tacticalInfo.style.display = 'none';

  try {
    let url = '/api/puzzle';
    const params = new URLSearchParams();
    if (currentPhaseFilters.length > 0) {
      currentPhaseFilters.forEach(phase => params.append('game_phases', phase));
    }
    if (currentTacticalFilter && currentTacticalFilter !== 'all') {
      params.append('tactical_patterns', currentTacticalFilter);
    }
    if (currentGameTypeFilters.length > 0) {
      currentGameTypeFilters.forEach(gameType => params.append('game_types', gameType));
    }
    if (currentColorFilter && currentColorFilter !== 'both') {
      params.append('colors', currentColorFilter);
    }
    if (params.toString()) {
      url += '?' + params.toString();
    }
    const resp = await fetch(url);
    const data = await resp.json();

    if (!resp.ok || data.detail || data.error) {
      const errorMsg = data.detail || data.error || '';

      // Determine error type from message
      if (errorMsg.toLowerCase().includes('no games found')) {
        showEmptyState('no_games');
      } else if (errorMsg.toLowerCase().includes('no blunders found')) {
        showEmptyState('no_blunders');
      } else if (errorMsg.toLowerCase().includes('no username configured')) {
        // Redirect to setup if no username configured
        window.location.href = '/setup';
        return;
      } else {
        showEmptyState('unknown');
      }
      return;
    }

    // Success - ensure trainer layout is visible
    hideEmptyState();

    puzzle = data;

    // Initialize game and board
    game = new Chess(puzzle.fen);

    const orientation = puzzle.player_color === 'black' ? 'black' : 'white';

    if (board) {
      board.destroy();
    }

    board = Chessboard('board', {
      position: puzzle.fen,
      orientation: orientation,
      draggable: true,
      pieceTheme: '/static/pieces/wikipedia/{piece}.png',
      onDragStart: onDragStart,
      onDrop: onDrop,
      onSnapEnd: onSnapEnd
    });

    // Update UI
    updateColorBadge(puzzle.player_color);
    updatePhaseBadge(puzzle.game_phase);
    updateTacticalBadge(puzzle.tactical_pattern);
    blunderMove.textContent = puzzle.blunder_san;
    evalBefore.textContent = puzzle.eval_before_display;
    evalAfter.textContent = puzzle.eval_after_display;
    cpLoss.textContent = (puzzle.cp_loss / 100).toFixed(1) + ' pawns';

    // Set eval bar to position before blunder
    updateEvalBar(puzzle.eval_before, puzzle.player_color);

    // Store best move info
    bestMoveDisplay.textContent = puzzle.best_move_san || '...';
    bestLineDisplay.textContent = puzzle.best_line ? puzzle.best_line.join(' ') : '...';

    // Show blunder highlight and arrow after a short delay (for board to render)
    setTimeout(() => {
      showBlunderHighlight();
      highlightLegend.style.display = 'flex';
      drawArrows();
      drawThreatHighlights();
    }, 100);

  } catch (err) {
    console.error('Failed to load puzzle:', err);
    showEmptyState('unknown');
  }
}

async function submitMove() {
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

  console.log('Submitting move with payload:', payload);

  try {
    const resp = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await resp.json();

    if (data.error) {
      showFeedback('incorrect', 'Error', data.error);
      return;
    }

    submitted = true;

    // Clear previous highlights and show new ones
    clearHighlights();

    if (data.is_best) {
      showFeedback('correct', 'Excellent!', 'You found the best move: ' + data.user_san);
      phaseIndicator.textContent = 'Correct!';
      phaseIndicator.className = 'phase explore';
      // Only show best move highlight (which is the same as user's move)
      showBestMoveHighlight();
      legendUser.style.display = 'none';
    } else if (data.is_blunder) {
      showFeedback('blunder-repeat', 'Same blunder!', 'You played the same blunder again: ' + data.user_san + '. The best move was ' + data.best_san);
      // Show blunder (user repeated it) and best move
      showBlunderHighlight();
      showBestMoveHighlight();
      legendUser.style.display = 'none';
    } else {
      // Check if the move is reasonable (within some threshold)
      const evalDiff = Math.abs(data.user_eval - puzzle.eval_before);
      if (evalDiff < 50) {
        showFeedback('correct', 'Good move!', 'Your move ' + data.user_san + ' is solid. Best was ' + data.best_san);
      } else {
        showFeedback('incorrect', 'Not quite', 'Your move: ' + data.user_san + ' (' + data.user_eval_display + '). Best was ' + data.best_san);
      }
      // Show user's move and best move
      showUserMoveHighlight(data.user_uci);
      showBestMoveHighlight();
      legendUser.style.display = 'flex';
    }

    // Show best move in legend
    legendBest.style.display = 'flex';

    // Reveal best move after submission
    revealBestMove();

    // Refresh stats after submission (HTMX-powered)
    if (typeof htmx !== 'undefined') {
      // Trigger the stats update event on body (listener expects 'from:body')
      htmx.trigger(document.body, 'statsUpdate');
    } else {
      console.warn('HTMX not loaded, stats will not auto-update');
    }

  } catch (err) {
    showFeedback('incorrect', 'Error', 'Failed to submit move');
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

  // Show highlights if not already shown (e.g., from "Show Best" button)
  if (!submitted) {
    clearHighlights();
    showBlunderHighlight();
    showBestMoveHighlight();
    legendBest.style.display = 'flex';
  }

  // Show tactical info and highlights
  if (puzzle) {
    showTacticalInfo(puzzle.tactical_pattern, puzzle.tactical_reason);
    drawTacticalHighlights();
  }

  // Redraw arrows to include best move arrow
  drawArrows();
}

function resetPosition() {
  if (!puzzle) return;
  game = new Chess(puzzle.fen);
  board.position(puzzle.fen);
  currentMove.textContent = '-';
  moveHistory = [];
  updateMoveHistory();

  if (!bestRevealed) {
    hideFeedback();
  }

  // Restore highlights and arrows after board reset
  setTimeout(() => {
    clearHighlights();
    if (bestRevealed) {
      showBlunderHighlight();
      showBestMoveHighlight();
      drawTacticalHighlights();
    } else {
      showBlunderHighlight();
    }
    drawArrows();
    drawThreatHighlights();
  }, 50);
}

function playBestMove() {
  if (!puzzle || !puzzle.best_move_uci) return;

  // Reset to original position first
  game = new Chess(puzzle.fen);

  // Play the best move
  const from = puzzle.best_move_uci.slice(0, 2);
  const to = puzzle.best_move_uci.slice(2, 4);
  const promotion = puzzle.best_move_uci.length > 4 ? puzzle.best_move_uci[4] : undefined;

  const move = game.move({ from, to, promotion });
  if (move) {
    board.position(game.fen());
    moveHistory = [move.san];
    updateMoveHistory();
    updateCurrentMove();
    historySection.style.display = 'block';
  }
}

function undoMove() {
  if (game.history().length === 0) return;
  game.undo();
  board.position(game.fen());
  moveHistory.pop();
  updateMoveHistory();
  updateCurrentMove();
}

function openLichessAnalysis() {
  if (!puzzle) return;
  // Use current board position (allows analyzing after making moves)
  const fen = game.fen();
  // Lichess analysis URL format: https://lichess.org/analysis/{fen}?color={white|black}
  // FEN needs to have spaces replaced with underscores for the URL
  const encodedFen = fen.replace(/ /g, '_');
  const color = puzzle.player_color;

  // Build arrows for blunder (red) and best move (green)
  // Lichess arrow format in hash: color letter + from + to (e.g., "Re2e4" for red arrow e2->e4)
  // R=red, G=green, B=blue, Y=yellow
  let arrows = [];

  // Only show arrows if we're at the original position (not after exploration)
  const atOriginalPosition = game.fen() === puzzle.fen;

  if (atOriginalPosition) {
    // Red arrow for blunder
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      const from = puzzle.blunder_uci.slice(0, 2);
      const to = puzzle.blunder_uci.slice(2, 4);
      arrows.push(`R${from}${to}`);
    }

    // Green arrow for best move
    if (puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      const from = puzzle.best_move_uci.slice(0, 2);
      const to = puzzle.best_move_uci.slice(2, 4);
      arrows.push(`G${from}${to}`);
    }
  }

  const arrowHash = arrows.length > 0 ? '#' + arrows.join(',') : '';
  const url = `https://lichess.org/analysis/${encodedFen}?color=${color}${arrowHash}`;
  window.open(url, '_blank');
}

// Phase filter functions
const PHASE_FILTER_STORAGE_KEY = 'blunder-tutor-phase-filters';

function updatePhaseFilters() {
  currentPhaseFilters = [];
  phaseFilterCheckboxes.forEach(checkbox => {
    if (checkbox.checked) {
      currentPhaseFilters.push(checkbox.value);
    }
  });
  localStorage.setItem(PHASE_FILTER_STORAGE_KEY, JSON.stringify(currentPhaseFilters));
}

function loadPhaseFiltersFromStorage() {
  const stored = localStorage.getItem(PHASE_FILTER_STORAGE_KEY);
  if (stored) {
    try {
      const phases = JSON.parse(stored);
      if (Array.isArray(phases)) {
        phaseFilterCheckboxes.forEach(checkbox => {
          checkbox.checked = phases.includes(checkbox.value);
        });
        currentPhaseFilters = phases;
      }
    } catch (e) {
      console.warn('Failed to parse stored phase filters:', e);
    }
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

// Event listeners
submitBtn.addEventListener('click', submitMove);
resetBtn.addEventListener('click', resetPosition);
showBestBtn.addEventListener('click', () => {
  revealBestMove();
  showFeedback('incorrect', 'Best move revealed', 'The best move was ' + puzzle.best_move_san);
});
nextBtn.addEventListener('click', loadPuzzle);
tryBestBtn.addEventListener('click', playBestMove);
undoBtn.addEventListener('click', undoMove);
lichessBtn.addEventListener('click', openLichessAnalysis);
showArrowsCheckbox.addEventListener('change', drawArrows);
showThreatsCheckbox.addEventListener('change', drawThreatHighlights);
if (showTacticsCheckbox) {
  showTacticsCheckbox.addEventListener('change', drawTacticalHighlights);
}
phaseFilterCheckboxes.forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    updatePhaseFilters();
    loadPuzzle();
  });
});

// Tactical filter event listeners
tacticalFilterBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    // Update active state
    tacticalFilterBtns.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');

    // Update filter and reload
    currentTacticalFilter = btn.dataset.pattern;
    localStorage.setItem('blunder-tutor-tactical-filter', currentTacticalFilter);
    loadPuzzle();
  });
});

// Game type filter event listeners
gameTypeCheckboxes.forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    updateGameTypeFilters();
    loadPuzzle();
  });
});

// Color filter event listeners
colorFilterRadios.forEach(radio => {
  radio.addEventListener('change', () => {
    updateColorFilter();
    loadPuzzle();
  });
});

// Collapsible filter panel event listeners
if (filtersHeader) {
  filtersHeader.addEventListener('click', toggleFiltersPanel);
}
if (filtersToggleBtn) {
  filtersToggleBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleFiltersPanel();
  });
}

// Load tactical filter from storage
function loadTacticalFilterFromStorage() {
  const stored = localStorage.getItem('blunder-tutor-tactical-filter');
  if (stored) {
    currentTacticalFilter = stored;
    tacticalFilterBtns.forEach(btn => {
      if (btn.dataset.pattern === stored) {
        btn.classList.add('active');
      } else {
        btn.classList.remove('active');
      }
    });
  }
}

// Game type filter functions
const GAME_TYPE_FILTER_STORAGE_KEY = 'blunder-tutor-game-type-filters';

function updateGameTypeFilters() {
  currentGameTypeFilters = [];
  gameTypeCheckboxes.forEach(checkbox => {
    if (checkbox.checked) {
      currentGameTypeFilters.push(checkbox.value);
    }
  });
  localStorage.setItem(GAME_TYPE_FILTER_STORAGE_KEY, JSON.stringify(currentGameTypeFilters));
}

function loadGameTypeFiltersFromStorage() {
  const stored = localStorage.getItem(GAME_TYPE_FILTER_STORAGE_KEY);
  if (stored) {
    try {
      const gameTypes = JSON.parse(stored);
      if (Array.isArray(gameTypes)) {
        gameTypeCheckboxes.forEach(checkbox => {
          checkbox.checked = gameTypes.includes(checkbox.value);
        });
        currentGameTypeFilters = gameTypes;
      }
    } catch (e) {
      console.warn('Failed to parse stored game type filters:', e);
      // Set defaults
      currentGameTypeFilters = ['bullet', 'blitz', 'rapid'];
      gameTypeCheckboxes.forEach(checkbox => {
        checkbox.checked = currentGameTypeFilters.includes(checkbox.value);
      });
    }
  } else {
    // Set defaults if nothing stored
    currentGameTypeFilters = ['bullet', 'blitz', 'rapid'];
    gameTypeCheckboxes.forEach(checkbox => {
      checkbox.checked = currentGameTypeFilters.includes(checkbox.value);
    });
  }
}

// Color filter functions
const COLOR_FILTER_STORAGE_KEY = 'blunder-tutor-color-filter';

function updateColorFilter() {
  colorFilterRadios.forEach(radio => {
    if (radio.checked) {
      currentColorFilter = radio.value;
    }
  });
  if (currentColorFilter === 'both') {
    localStorage.removeItem(COLOR_FILTER_STORAGE_KEY);
  } else {
    localStorage.setItem(COLOR_FILTER_STORAGE_KEY, currentColorFilter);
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

// Collapsible filter panel functions
const FILTERS_COLLAPSED_KEY = 'blunder-tutor-filters-collapsed';

function toggleFiltersPanel() {
  filtersCollapsed = !filtersCollapsed;
  updateFiltersPanelState();
  localStorage.setItem(FILTERS_COLLAPSED_KEY, JSON.stringify(filtersCollapsed));
}

function updateFiltersPanelState() {
  if (filtersCollapsed) {
    filtersContent.classList.add('collapsed');
    filtersChevron.classList.add('collapsed');
  } else {
    filtersContent.classList.remove('collapsed');
    filtersChevron.classList.remove('collapsed');
  }
}

function loadFiltersPanelState() {
  const stored = localStorage.getItem(FILTERS_COLLAPSED_KEY);
  if (stored) {
    try {
      filtersCollapsed = JSON.parse(stored);
      updateFiltersPanelState();
    } catch (e) {
      filtersCollapsed = false;
    }
  }
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && !submitted) {
    submitMove();
  } else if (e.key === 'n' || e.key === 'N') {
    loadPuzzle();
  } else if (e.key === 'r' || e.key === 'R') {
    resetPosition();
  } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
    undoMove();
  }
});

// Initialize
loadPhaseFiltersFromStorage();
loadTacticalFilterFromStorage();
loadGameTypeFiltersFromStorage();
loadColorFilterFromStorage();
loadFiltersPanelState();
loadPuzzle();
// Stats are loaded automatically via HTMX on page load
