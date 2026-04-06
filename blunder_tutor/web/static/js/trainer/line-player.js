import * as state from './state.js';
import * as ui from './ui.js';
import { redrawAllHighlights } from './board-visuals.js';
import { isPlayFullLineEnabled } from './filters.js';

export function clearLineNavigation() {
  state.set('linePositions', []);
  state.set('lineViewIndex', -1);
}

function playSingleBestMove() {
  const puzzle = state.get('puzzle');
  const game = new Chess(puzzle.fen);
  state.set('game', game);

  const from = puzzle.best_move_uci.slice(0, 2);
  const to = puzzle.best_move_uci.slice(2, 4);
  const promotion = puzzle.best_move_uci.length > 4 ? puzzle.best_move_uci[4] : undefined;

  const move = game.move({ from, to, promotion });
  if (move) {
    const board = state.get('board');
    board.setPosition(game.fen(), game);
    state.set('moveHistory', [move.san]);
    ui.updateMoveHistory([move.san]);
    ui.updateCurrentMove(game);
    ui.showHistorySection();
  }
}

async function playFullLineAnimated() {
  const gen = state.nextAnimationGeneration();
  state.set('animatingLine', true);

  const boardResultCard = ui.getEl('boardResultCard');

  const fadeOut = () => new Promise(resolve => {
    boardResultCard.classList.add('fading-out');
    boardResultCard.classList.remove('visible');
    const onEnd = () => {
      boardResultCard.removeEventListener('transitionend', onEnd);
      boardResultCard.classList.remove('fading-out');
      resolve();
    };
    boardResultCard.addEventListener('transitionend', onEnd);
  });

  if (boardResultCard.classList.contains('visible')) {
    await fadeOut();
  }

  const puzzle = state.get('puzzle');
  const game = new Chess(puzzle.fen);
  state.set('game', game);
  state.set('moveHistory', []);
  state.set('linePositions', [{ fen: puzzle.fen, moveHistory: [] }]);
  ui.showHistorySection();

  const moveHistory = [];

  for (const san of puzzle.best_line) {
    if (gen !== state.get('animationGeneration')) return;
    const move = game.move(san);
    if (!move) break;
    const board = state.get('board');
    board.setPosition(game.fen(), game);
    moveHistory.push(move.san);
    state.set('moveHistory', [...moveHistory]);
    state.pushLinePosition({ fen: game.fen(), moveHistory: [...moveHistory] });
    ui.updateMoveHistory(moveHistory);
    ui.updateCurrentMove(game);
    redrawAllHighlights();
    await new Promise(r => setTimeout(r, 1000));
  }

  if (gen === state.get('animationGeneration')) {
    state.set('animatingLine', false);
    state.set('lineViewIndex', state.get('linePositions').length - 1);
  }
}

export function playBestMove() {
  const puzzle = state.get('puzzle');
  if (!puzzle || !puzzle.best_move_uci) return;
  if (state.isAnimating()) return;

  const useFullLine = isPlayFullLineEnabled()
    && puzzle.best_line && puzzle.best_line.length > 1;

  if (useFullLine) {
    playFullLineAnimated();
    return;
  }

  const wasVisible = ui.isBoardResultVisible();
  if (wasVisible) ui.hideBoardResult();

  if (wasVisible) {
    setTimeout(playSingleBestMove, 100);
  } else {
    playSingleBestMove();
  }
}

export function navigateLine(direction) {
  const linePositions = state.get('linePositions');
  if (linePositions.length === 0) return;

  const lineViewIndex = state.get('lineViewIndex');
  const newIndex = lineViewIndex + direction;
  if (newIndex < 0 || newIndex >= linePositions.length) return;

  state.set('lineViewIndex', newIndex);
  const pos = linePositions[newIndex];
  const game = new Chess(pos.fen);
  state.set('game', game);
  const board = state.get('board');
  board.setPosition(pos.fen, game);
  state.set('moveHistory', [...pos.moveHistory]);
  ui.updateMoveHistory(pos.moveHistory);
  ui.updateCurrentMove(game);
  redrawAllHighlights();
}
