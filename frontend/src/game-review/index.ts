import { MoveSequence, ReadOnlyBoard, PlaybackController } from '../shared/sequence-player';
import { updateEvalBar } from '../trainer/eval-bar';
import { client } from '../shared/api';
import { EvalChart, evalFromWhite } from './eval-chart';
import { applyBoardBackground, applyPieceSet } from '../trainer/board-visuals';

interface ReviewMove {
  san: string;
  move_number: number;
  player: string;
  ply: number;
  eval_after: number;
  classification?: string;
}

interface ReviewGame {
  username?: string;
  white: string;
  black: string;
  result?: string;
  game_url?: string;
}

interface ReviewData {
  moves: ReviewMove[];
  game: ReviewGame;
  analyzed: boolean;
}

interface BoardSettings {
  board_light: string;
  board_dark: string;
  piece_set?: string;
}

function deriveOutcome(result: string, playerColor: string): string {
  if (result === '1/2-1/2') return t('game_review.result.draw');
  const whiteWon = result === '1-0';
  const playerWon = (playerColor === 'white') === whiteWon;
  return playerWon ? t('game_review.result.win') : t('game_review.result.loss');
}

let sequence: MoveSequence | null = null;
let board: ReadOnlyBoard | null = null;
let playback: PlaybackController | null = null;
let evalChart: EvalChart | null = null;
let moves: ReviewMove[] = [];
let orientation = 'white';

function getGameId(): string | null {
  const path = window.location.pathname;
  const match = path.match(/^\/game\/(.+)$/);
  return match ? decodeURIComponent(match[1]!) : null;
}

function getStartPly(): number | null {
  const params = new URLSearchParams(window.location.search);
  const ply = params.get('ply');
  return ply ? parseInt(ply, 10) : null;
}

function showError(message: string): void {
  document.getElementById('reviewLoading')?.classList.add('hidden');
  document.getElementById('reviewContent')?.classList.add('hidden');
  const errorEl = document.getElementById('reviewError');
  errorEl?.classList.remove('hidden');
  const msgEl = document.getElementById('reviewErrorMessage');
  if (msgEl) msgEl.textContent = message;
}

interface MovePair {
  white: (ReviewMove & { index: number }) | null;
  black: (ReviewMove & { index: number }) | null;
}

function buildMoveList(reviewMoves: ReviewMove[]): void {
  const container = document.getElementById('reviewMoveList');
  if (!container) return;
  container.innerHTML = '';

  const movesByNumber = new Map<number, MovePair>();
  for (let i = 0; i < reviewMoves.length; i++) {
    const m = reviewMoves[i]!;
    const num = m.move_number;
    if (!movesByNumber.has(num)) {
      movesByNumber.set(num, { white: null, black: null });
    }
    const entry = movesByNumber.get(num)!;
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

function buildMoveCell(moveInfo: (ReviewMove & { index: number }) | null): HTMLSpanElement {
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

  cell.dataset.index = String(moveInfo.index);
  cell.addEventListener('click', () => {
    goToMoveIndex(moveInfo.index);
  });

  return cell;
}

function goToMoveIndex(index: number): void {
  playback!.pause();
  sequence!.goTo(index);
  board!.setPosition(sequence!.fen, sequence!.lastMove);
  updateUI();
}

function updateUI(): void {
  const idx = sequence!.currentIndex;

  document.querySelectorAll('.review-move-cell.active').forEach(el => {
    el.classList.remove('active');
  });
  const activeCell = document.querySelector(`.review-move-cell[data-index="${idx}"]`);
  if (activeCell) {
    activeCell.classList.add('active');
    activeCell.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  const fillEl = document.getElementById('reviewEvalBarFill');
  const valueEl = document.getElementById('reviewEvalValue');
  if (fillEl && valueEl) {
    if (moves.length > 0 && idx >= 0 && idx < moves.length) {
      const move = moves[idx]!;
      const evalWhite = evalFromWhite(move);
      updateEvalBar(evalWhite, 'white', fillEl, valueEl);
    } else {
      updateEvalBar(0, 'white', fillEl, valueEl);
    }
  }

  if (evalChart) {
    evalChart.setActivePly(idx);
  }

  updateNavButtons();
}

function updateNavButtons(): void {
  const atStart = sequence!.isAtStart;
  const atEnd = sequence!.isAtEnd;
  const playing = playback!.isPlaying;

  (document.getElementById('reviewFirst') as HTMLButtonElement | null)!.disabled = atStart;
  (document.getElementById('reviewPrev') as HTMLButtonElement | null)!.disabled = atStart;
  (document.getElementById('reviewNext') as HTMLButtonElement | null)!.disabled = atEnd;
  (document.getElementById('reviewLast') as HTMLButtonElement | null)!.disabled = atEnd;

  const playBtn = document.getElementById('reviewPlayPause');
  if (playBtn) {
    playBtn.innerHTML = playing ? '&#x23F8;' : '&#x25B6;';
    playBtn.title = playing ? t('game_review.controls.pause') : t('game_review.controls.play');
  }
}

function flipBoard(): void {
  orientation = orientation === 'white' ? 'black' : 'white';
  board!.setOrientation(orientation);

  const colorIndicator = document.getElementById('reviewColorIndicator');
  const colorText = document.getElementById('reviewColorText');
  if (colorIndicator) colorIndicator.className = `color-indicator ${orientation}-piece`;
  if (colorText) colorText.textContent = orientation === 'black' ? t('chess.color.black') : t('chess.color.white');

  updateUI();
}

function goFirst(): void {
  playback!.pause();
  sequence!.goToStart();
  board!.setPosition(sequence!.fen, null);
  updateUI();
}

function goPrev(): void {
  playback!.pause();
  const result = sequence!.stepBack();
  if (result) board!.setPosition(sequence!.fen, result.lastMove);
  updateUI();
}

function goNext(): void {
  playback!.pause();
  const result = sequence!.stepForward();
  if (result) board!.setPosition(result.fen, result.lastMove);
  updateUI();
}

function goLast(): void {
  playback!.pause();
  sequence!.goToEnd();
  board!.setPosition(sequence!.fen, sequence!.lastMove);
  updateUI();
}

function togglePlayPause(): void {
  if (sequence!.isAtEnd) {
    sequence!.goToStart();
    board!.setPosition(sequence!.fen, null);
    updateUI();
  }
  playback!.toggle();
  updateNavButtons();
}

function setupControls(): void {
  document.getElementById('reviewFirst')?.addEventListener('click', goFirst);
  document.getElementById('reviewPrev')?.addEventListener('click', goPrev);
  document.getElementById('reviewNext')?.addEventListener('click', goNext);
  document.getElementById('reviewLast')?.addEventListener('click', goLast);
  document.getElementById('reviewPlayPause')?.addEventListener('click', togglePlayPause);
  document.getElementById('reviewFlip')?.addEventListener('click', flipBoard);

  document.addEventListener('keydown', (e) => {
    const target = e.target as HTMLElement;
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return;

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

function populateGameInfo(game: ReviewGame): void {
  const colorIndicator = document.getElementById('reviewColorIndicator');
  const colorText = document.getElementById('reviewColorText');
  const playerColor = orientation === 'black' ? 'black' : 'white';
  if (colorIndicator) colorIndicator.className = `color-indicator ${playerColor}-piece`;
  if (colorText) colorText.textContent = playerColor === 'black' ? t('chess.color.black') : t('chess.color.white');

  const resultBadge = document.getElementById('reviewResultBadge');
  if (game.result && resultBadge) {
    const outcome = deriveOutcome(game.result, playerColor);
    resultBadge.textContent = outcome;
    resultBadge.classList.remove('hidden');
    document.getElementById('reviewResultSep')?.classList.remove('hidden');
  }

  const linkEl = document.getElementById('reviewSourceLink') as HTMLAnchorElement | null;
  if (game.game_url && linkEl) {
    linkEl.href = game.game_url;
    linkEl.classList.remove('hidden');
    document.getElementById('reviewLinkSep')?.classList.remove('hidden');
  }
}

async function init(): Promise<void> {
  const gameId = getGameId();
  if (!gameId) {
    showError(t('game_review.not_found'));
    return;
  }

  try {
    const [data, boardSettings] = await Promise.all([
      client.gameReview.getReview(gameId) as Promise<ReviewData>,
      client.settings.getBoard().catch(() => null) as Promise<BoardSettings | null>,
    ]);
    moves = data.moves;

    if (data.game.username) {
      const uname = data.game.username.toLowerCase();
      if (data.game.black.toLowerCase() === uname) {
        orientation = 'black';
      }
    }

    document.getElementById('reviewLoading')?.classList.add('hidden');
    document.getElementById('reviewContent')?.classList.remove('hidden');

    populateGameInfo(data.game);

    if (boardSettings) {
      const root = document.documentElement;
      root.style.setProperty('--board-light', boardSettings.board_light);
      root.style.setProperty('--board-dark', boardSettings.board_dark);
      applyBoardBackground(boardSettings.board_light, boardSettings.board_dark);
      applyPieceSet(boardSettings.piece_set || 'gioco');
    }

    if (!data.analyzed) {
      document.getElementById('reviewNotAnalyzed')?.classList.remove('hidden');
      document.getElementById('reviewEvalBarContainer')?.classList.add('hidden');
      document.getElementById('reviewEvalChartContainer')?.classList.add('hidden');
    }

    const sanMoves = moves.map(m => m.san);
    buildMoveList(moves);

    sequence = new MoveSequence(sanMoves);
    const boardEl = document.getElementById('reviewBoard');
    if (!boardEl) return;
    board = new ReadOnlyBoard(boardEl, {
      orientation,
      fen: sequence.fen,
    });

    playback = new PlaybackController({
      speed: 1000,
      onTick: () => {
        if (sequence!.isAtEnd) {
          playback!.pause();
          updateNavButtons();
          return;
        }
        const result = sequence!.stepForward();
        if (result) board!.setPosition(result.fen, result.lastMove);
        updateUI();
      },
    });

    if (data.analyzed) {
      const canvas = document.getElementById('reviewEvalChart') as HTMLCanvasElement | null;
      if (canvas) {
        evalChart = new EvalChart(canvas);
        evalChart.render(moves);
        evalChart.onClick((index) => {
          goToMoveIndex(index);
        });
      }
    }

    setupControls();

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
    if ((err as { status?: number }).status === 404) {
      showError(t('game_review.not_found'));
    } else {
      showError(t('common.error'));
      console.error('Failed to load game review:', err);
    }
  }
}

init();
