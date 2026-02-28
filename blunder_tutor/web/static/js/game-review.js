import { MoveSequence, ReadOnlyBoard, PlaybackController } from './sequence-player.js';
import { updateEvalBar } from './trainer/eval-bar.js';
import { client } from './api.js';
import { EvalChart, evalFromWhite } from './game-review/eval-chart.js';
import { applyBoardBackground, applyPieceSet } from './trainer/board-visuals.js';

const t = window.t || ((key) => key);

function deriveOutcome(result, playerColor) {
  if (result === '1/2-1/2') return t('game_review.result.draw');
  const whiteWon = result === '1-0';
  const playerWon = (playerColor === 'white') === whiteWon;
  return playerWon ? t('game_review.result.win') : t('game_review.result.loss');
}

let sequence = null;
let board = null;
let playback = null;
let evalChart = null;
let moves = [];
let orientation = 'white';

function getGameId() {
  const path = window.location.pathname;
  const match = path.match(/^\/game\/(.+)$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function getStartPly() {
  const params = new URLSearchParams(window.location.search);
  const ply = params.get('ply');
  return ply ? parseInt(ply, 10) : null;
}

function showError(message) {
  document.getElementById('reviewLoading').classList.add('hidden');
  document.getElementById('reviewContent').classList.add('hidden');
  const errorEl = document.getElementById('reviewError');
  errorEl.classList.remove('hidden');
  document.getElementById('reviewErrorMessage').textContent = message;
}

function buildMoveList(moves) {
  const container = document.getElementById('reviewMoveList');
  container.innerHTML = '';

  const movesByNumber = new Map();
  for (let i = 0; i < moves.length; i++) {
    const m = moves[i];
    const num = m.move_number;
    if (!movesByNumber.has(num)) {
      movesByNumber.set(num, { white: null, black: null });
    }
    const entry = movesByNumber.get(num);
    if (m.player === 'white') {
      entry.white = { ...m, index: i };
    } else {
      entry.black = { ...m, index: i };
    }
  }

  for (const [num, pair] of movesByNumber) {
    const row = document.createElement('div');
    row.className = 'review-move-row';

    const numEl = document.createElement('span');
    numEl.className = 'review-move-num';
    numEl.textContent = num + '.';
    row.appendChild(numEl);

    row.appendChild(buildMoveCell(pair.white));
    row.appendChild(buildMoveCell(pair.black));

    container.appendChild(row);
  }
}

function buildMoveCell(moveInfo) {
  const cell = document.createElement('span');
  cell.className = 'review-move-cell';

  if (!moveInfo) {
    cell.textContent = '';
    return cell;
  }

  if (moveInfo.classification && moveInfo.classification !== 'normal') {
    const dot = document.createElement('span');
    dot.className = 'review-move-dot ' + moveInfo.classification;
    cell.appendChild(dot);
  }

  const text = document.createTextNode(moveInfo.san);
  cell.appendChild(text);

  cell.dataset.index = moveInfo.index;
  cell.addEventListener('click', () => {
    goToMoveIndex(moveInfo.index);
  });

  return cell;
}

function goToMoveIndex(index) {
  playback.pause();
  sequence.goTo(index);
  board.setPosition(sequence.fen, sequence.lastMove);
  updateUI();
}

function updateUI() {
  const idx = sequence.currentIndex;

  // Update active move highlight
  document.querySelectorAll('.review-move-cell.active').forEach(el => {
    el.classList.remove('active');
  });
  const activeCell = document.querySelector(`.review-move-cell[data-index="${idx}"]`);
  if (activeCell) {
    activeCell.classList.add('active');
    activeCell.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  // Update eval bar — always from white's POV to stay in sync with the chart
  if (moves.length > 0 && idx >= 0 && idx < moves.length) {
    const move = moves[idx];
    const evalWhite = evalFromWhite(move);
    updateEvalBar(
      evalWhite,
      'white',
      document.getElementById('reviewEvalBarFill'),
      document.getElementById('reviewEvalValue')
    );
  } else {
    updateEvalBar(
      0,
      'white',
      document.getElementById('reviewEvalBarFill'),
      document.getElementById('reviewEvalValue')
    );
  }

  // Update eval chart indicator
  if (evalChart) {
    evalChart.setActivePly(idx);
  }

  // Update nav button states
  updateNavButtons();
}

function updateNavButtons() {
  const atStart = sequence.isAtStart;
  const atEnd = sequence.isAtEnd;
  const playing = playback.isPlaying;

  document.getElementById('reviewFirst').disabled = atStart;
  document.getElementById('reviewPrev').disabled = atStart;
  document.getElementById('reviewNext').disabled = atEnd;
  document.getElementById('reviewLast').disabled = atEnd;

  const playBtn = document.getElementById('reviewPlayPause');
  playBtn.innerHTML = playing ? '&#x23F8;' : '&#x25B6;';
  playBtn.title = playing ? t('game_review.controls.pause') : t('game_review.controls.play');
}

function flipBoard() {
  orientation = orientation === 'white' ? 'black' : 'white';
  board.setOrientation(orientation);

  const colorIndicator = document.getElementById('reviewColorIndicator');
  const colorText = document.getElementById('reviewColorText');
  colorIndicator.className = `color-indicator ${orientation}-piece`;
  colorText.textContent = orientation === 'black' ? t('chess.color.black') : t('chess.color.white');

  updateUI();
}

function goFirst() {
  playback.pause();
  sequence.goToStart();
  board.setPosition(sequence.fen, null);
  updateUI();
}

function goPrev() {
  playback.pause();
  const result = sequence.stepBack();
  if (result) board.setPosition(sequence.fen, result.lastMove);
  updateUI();
}

function goNext() {
  playback.pause();
  const result = sequence.stepForward();
  if (result) board.setPosition(result.fen, result.lastMove);
  updateUI();
}

function goLast() {
  playback.pause();
  sequence.goToEnd();
  board.setPosition(sequence.fen, sequence.lastMove);
  updateUI();
}

function togglePlayPause() {
  if (sequence.isAtEnd) {
    sequence.goToStart();
    board.setPosition(sequence.fen, null);
    updateUI();
  }
  playback.toggle();
  updateNavButtons();
}

function setupControls() {
  document.getElementById('reviewFirst').addEventListener('click', goFirst);
  document.getElementById('reviewPrev').addEventListener('click', goPrev);
  document.getElementById('reviewNext').addEventListener('click', goNext);
  document.getElementById('reviewLast').addEventListener('click', goLast);
  document.getElementById('reviewPlayPause').addEventListener('click', togglePlayPause);
  document.getElementById('reviewFlip').addEventListener('click', flipBoard);

  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

    switch (e.key) {
      case 'ArrowLeft':  e.preventDefault(); goPrev(); break;
      case 'ArrowRight': e.preventDefault(); goNext(); break;
      case 'Home':       e.preventDefault(); goFirst(); break;
      case 'End':        e.preventDefault(); goLast(); break;
      case 'f': case 'F': flipBoard(); break;
      case ' ':          e.preventDefault(); togglePlayPause(); break;
    }
  });
}

function populateGameInfo(game) {
  // Color indicator
  const colorIndicator = document.getElementById('reviewColorIndicator');
  const colorText = document.getElementById('reviewColorText');
  const playerColor = orientation === 'black' ? 'black' : 'white';
  colorIndicator.className = `color-indicator ${playerColor}-piece`;
  colorText.textContent = playerColor === 'black' ? t('chess.color.black') : t('chess.color.white');

  // Result badge (win/loss/draw from player's perspective)
  const resultBadge = document.getElementById('reviewResultBadge');
  if (game.result) {
    const outcome = deriveOutcome(game.result, playerColor);
    resultBadge.textContent = outcome;
    resultBadge.classList.remove('hidden');
    document.getElementById('reviewResultSep').classList.remove('hidden');
  }

  // Source link
  const linkEl = document.getElementById('reviewSourceLink');
  if (game.game_url) {
    linkEl.href = game.game_url;
    linkEl.classList.remove('hidden');
    document.getElementById('reviewLinkSep').classList.remove('hidden');
  }
}

async function init() {
  const gameId = getGameId();
  if (!gameId) {
    showError(t('game_review.not_found'));
    return;
  }

  try {
    const [data, boardSettings] = await Promise.all([
      client.gameReview.getReview(gameId),
      client.settings.getBoard().catch(() => null),
    ]);
    moves = data.moves;

    // Determine board orientation
    if (data.game.username) {
      const uname = data.game.username.toLowerCase();
      if (data.game.black.toLowerCase() === uname) {
        orientation = 'black';
      }
    }

    // Hide loading, show content
    document.getElementById('reviewLoading').classList.add('hidden');
    document.getElementById('reviewContent').classList.remove('hidden');

    // Populate game info
    populateGameInfo(data.game);

    // Apply board theme from settings
    if (boardSettings) {
      const root = document.documentElement;
      root.style.setProperty('--board-light', boardSettings.board_light);
      root.style.setProperty('--board-dark', boardSettings.board_dark);
      applyBoardBackground(boardSettings.board_light, boardSettings.board_dark);
      applyPieceSet(boardSettings.piece_set || 'gioco');
    }

    // Show not-analyzed message if needed
    if (!data.analyzed) {
      document.getElementById('reviewNotAnalyzed').classList.remove('hidden');
      document.getElementById('reviewEvalBarContainer').classList.add('hidden');
      document.getElementById('reviewEvalChartContainer').classList.add('hidden');
    }

    // Build move list
    const sanMoves = moves.map(m => m.san);
    buildMoveList(moves);

    // Init board
    sequence = new MoveSequence(sanMoves);
    board = new ReadOnlyBoard(document.getElementById('reviewBoard'), {
      orientation,
      fen: sequence.fen,
    });

    // Init playback
    playback = new PlaybackController({
      speed: 1000,
      onTick: () => {
        if (sequence.isAtEnd) {
          playback.pause();
          updateNavButtons();
          return;
        }
        const result = sequence.stepForward();
        if (result) board.setPosition(result.fen, result.lastMove);
        updateUI();
      },
    });

    // Init eval chart
    if (data.analyzed) {
      const canvas = document.getElementById('reviewEvalChart');
      evalChart = new EvalChart(canvas);
      evalChart.render(moves);
      evalChart.onClick((index) => {
        goToMoveIndex(index);
      });
    }

    // Setup controls
    setupControls();

    // Handle ?ply=N deep link
    const startPly = getStartPly();
    if (startPly !== null) {
      const moveIndex = moves.findIndex(m => m.ply === startPly);
      if (moveIndex >= 0) {
        goToMoveIndex(moveIndex);
        return;
      }
    }

    updateUI();

  } catch (err) {
    if (err.status === 404) {
      showError(t('game_review.not_found'));
    } else {
      showError(t('common.error'));
      console.error('Failed to load game review:', err);
    }
  }
}

init();
