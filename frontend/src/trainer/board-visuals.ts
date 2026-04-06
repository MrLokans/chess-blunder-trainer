import { client } from '../shared/api';
import * as state from './state';
import type { BoardSettings } from './state';
import {
  buildBlunderHighlight, buildBestMoveHighlight, buildUserMoveHighlight,
  buildTacticalHighlights, mergeHighlights,
} from './highlights';
import { buildThreatHighlights } from './threats';

let boardStyleEl: HTMLStyleElement | null = null;
let pieceStyleEl: HTMLStyleElement | null = null;

export function applyBoardBackground(light: string, dark: string): void {
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

export function applyPieceSet(pieceSet: string): void {
  const pieces = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
  const colorMap: Record<string, string> = { white: 'w', black: 'b' };
  const pieceMap: Record<string, string> = { pawn: 'P', rook: 'R', knight: 'N', bishop: 'B', queen: 'Q', king: 'K' };

  let css = '';
  for (const color of ['white', 'black']) {
    for (const role of pieces) {
      const file = `${colorMap[color]}${pieceMap[role]}`;
      const url = `/static/pieces/${pieceSet}/${file}.svg`;
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

export function redrawAllHighlights(): Map<string, string> | undefined {
  const board = state.get('board');
  const puzzle = state.get('puzzle');
  const game = state.get('game');
  if (!board || !puzzle) return undefined;

  const showThreatsEl = document.getElementById('showThreats') as HTMLInputElement | null;
  const showTacticsEl = document.getElementById('showTactics') as HTMLInputElement | null;

  const blunder = buildBlunderHighlight(puzzle);
  const best = state.get('bestRevealed') ? buildBestMoveHighlight(puzzle) : new Map<string, string>();
  const threats = buildThreatHighlights(game, showThreatsEl ? showThreatsEl.checked : false);
  const tactical = buildTacticalHighlights(
    puzzle, game, state.get('bestRevealed'),
    showTacticsEl ? showTacticsEl.checked : false,
  );

  const merged = mergeHighlights(blunder, best, threats, tactical);
  board.setCustomHighlight(merged.size > 0 ? merged : undefined);
  return tactical;
}

export function redrawAllHighlightsWithUser(userUci: string): Map<string, string> | undefined {
  const board = state.get('board');
  const puzzle = state.get('puzzle');
  const game = state.get('game');
  if (!board || !puzzle) return undefined;

  const showThreatsEl = document.getElementById('showThreats') as HTMLInputElement | null;
  const showTacticsEl = document.getElementById('showTactics') as HTMLInputElement | null;

  const blunder = buildBlunderHighlight(puzzle);
  const best = buildBestMoveHighlight(puzzle);
  const user = buildUserMoveHighlight(userUci);
  const threats = buildThreatHighlights(game, showThreatsEl ? showThreatsEl.checked : false);
  const tactical = buildTacticalHighlights(
    puzzle, game, state.get('bestRevealed'),
    showTacticsEl ? showTacticsEl.checked : false,
  );

  const merged = mergeHighlights(blunder, best, user, threats, tactical);
  board.setCustomHighlight(merged.size > 0 ? merged : undefined);
  return tactical;
}

export function redrawArrows(): void {
  const board = state.get('board');
  const puzzle = state.get('puzzle');
  const game = state.get('game');
  if (!board || !puzzle) return;

  const showArrowsEl = document.getElementById('showArrows') as HTMLInputElement | null;
  if (showArrowsEl && !showArrowsEl.checked) {
    board.clearArrows();
    return;
  }

  const atOriginalPosition = game !== null && game.fen() === puzzle.fen;
  const arrows: Array<{ from: string; to: string; color: string }> = [];

  if (atOriginalPosition) {
    if (puzzle.blunder_uci && puzzle.blunder_uci.length >= 4) {
      arrows.push({
        from: puzzle.blunder_uci.slice(0, 2),
        to: puzzle.blunder_uci.slice(2, 4),
        color: 'red',
      });
    }
    if (state.get('bestRevealed') && puzzle.best_move_uci && puzzle.best_move_uci.length >= 4) {
      arrows.push({
        from: puzzle.best_move_uci.slice(0, 2),
        to: puzzle.best_move_uci.slice(2, 4),
        color: 'green',
      });
    }
  }

  if (arrows.length > 0) {
    board.drawArrows(arrows);
  } else {
    board.clearArrows();
  }
}

export async function loadBoardSettings(): Promise<void> {
  try {
    const settings = await client.settings.getBoard() as BoardSettings;
    state.set('boardSettings', settings);
    const root = document.documentElement;
    root.style.setProperty('--board-light', settings.board_light);
    root.style.setProperty('--board-dark', settings.board_dark);
    applyBoardBackground(settings.board_light, settings.board_dark);
    applyPieceSet(settings.piece_set || 'gioco');
  } catch (err) {
    console.warn('Failed to load board settings:', err);
  }
}
