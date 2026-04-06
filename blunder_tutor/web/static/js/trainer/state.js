import { bus } from '../event-bus.js';

const INITIAL_STATE = {
  board: null,
  game: null,
  puzzle: null,
  submitted: false,
  bestRevealed: false,
  moveHistory: [],
  boardFlipped: false,
  animatingLine: false,
  animatingPreMove: false,
  animationGeneration: 0,
  linePositions: [],
  lineViewIndex: -1,
  currentStarred: false,
  boardSettings: {
    piece_set: 'gioco',
    board_light: '#E0E0E0',
    board_dark: '#A0A0A0',
  },
};

const state = { ...INITIAL_STATE, moveHistory: [], linePositions: [], boardSettings: { ...INITIAL_STATE.boardSettings } };

export function isAnimating() {
  return state.animatingLine || state.animatingPreMove;
}

export function get(key) {
  return state[key];
}

export function set(key, value) {
  const prev = state[key];
  state[key] = value;
  bus.emit('state:changed', { key, value, prev });
  bus.emit(`state:${key}`, { value, prev });
}

export function resetForNewPuzzle() {
  state.submitted = false;
  state.bestRevealed = false;
  state.boardFlipped = false;
  state.moveHistory = [];
  state.linePositions = [];
  state.lineViewIndex = -1;
  state.animatingLine = false;
  state.animatingPreMove = false;
  state.currentStarred = false;
  bus.emit('state:reset');
}

export function nextAnimationGeneration() {
  state.animationGeneration++;
  return state.animationGeneration;
}

export function pushMove(san) {
  state.moveHistory.push(san);
}

export function popMove() {
  return state.moveHistory.pop();
}

export function pushLinePosition(pos) {
  state.linePositions.push(pos);
}

export function snapshot() {
  return { ...state, moveHistory: [...state.moveHistory], linePositions: [...state.linePositions] };
}
