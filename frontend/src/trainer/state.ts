import { bus } from '../shared/event-bus';

export interface BoardSettings {
  piece_set: string;
  board_light: string;
  board_dark: string;
}

export interface BoardAdapter {
  setPosition(fen: string, game: ChessInstance): void;
  setOrientation(color: 'white' | 'black'): void;
  setCoordinates(enabled: boolean): void;
  drawArrows(arrows: Array<{ from: string; to: string; color: string }>): void;
  clearArrows(): void;
  setCustomHighlight(customMap: Map<string, string> | undefined): void;
  clearCustomHighlight(): void;
  animatePreMove(
    puzzleFen: string,
    from: string,
    to: string,
    game: ChessInstance,
    callback?: () => void,
  ): void;
  updateMovable(game: ChessInstance): void;
  destroy(): void;
}

export interface PuzzleData {
  game_id: string;
  fen: string;
  ply: number;
  blunder_uci: string;
  blunder_san: string;
  best_move_uci: string;
  best_move_san: string;
  best_line: string[];
  player_color: 'white' | 'black';
  eval_before: number;
  eval_after: number;
  eval_before_display: string;
  eval_after_display: string;
  cp_loss: number;
  game_phase: string;
  tactical_pattern: string | null;
  tactical_reason: string | null;
  tactical_squares: string[];
  explanation_blunder: string | null;
  explanation_best: string | null;
  game_url: string | null;
  difficulty: string;
  pre_move_uci: string | null;
  pre_move_fen: string | null;
  best_move_eval: number | null;
}

export interface LinePosition {
  fen: string;
  moveHistory: string[];
}

export interface TrainerState {
  board: BoardAdapter | null;
  game: ChessInstance | null;
  puzzle: PuzzleData | null;
  submitted: boolean;
  bestRevealed: boolean;
  moveHistory: string[];
  boardFlipped: boolean;
  animatingLine: boolean;
  animatingPreMove: boolean;
  animationGeneration: number;
  linePositions: LinePosition[];
  lineViewIndex: number;
  currentStarred: boolean;
  boardSettings: BoardSettings;
}

const INITIAL_STATE: TrainerState = {
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

const state: TrainerState = {
  ...INITIAL_STATE,
  moveHistory: [],
  linePositions: [],
  boardSettings: { ...INITIAL_STATE.boardSettings },
};

export function isAnimating(): boolean {
  return state.animatingLine || state.animatingPreMove;
}

export function get<K extends keyof TrainerState>(key: K): TrainerState[K] {
  return state[key];
}

export function set<K extends keyof TrainerState>(key: K, value: TrainerState[K]): void {
  const prev = state[key];
  state[key] = value;
  bus.emit('state:changed', { key, value, prev } as never);
  bus.emit(`state:${key}` as never, { value, prev } as never);
}

export function resetForNewPuzzle(): void {
  state.submitted = false;
  state.bestRevealed = false;
  state.boardFlipped = false;
  state.moveHistory = [];
  state.linePositions = [];
  state.lineViewIndex = -1;
  state.animatingLine = false;
  state.animatingPreMove = false;
  state.currentStarred = false;
  bus.emit('state:reset' as never);
}

export function nextAnimationGeneration(): number {
  state.animationGeneration++;
  return state.animationGeneration;
}

export function pushMove(san: string): void {
  state.moveHistory.push(san);
}

export function popMove(): string | undefined {
  return state.moveHistory.pop();
}

export function pushLinePosition(pos: LinePosition): void {
  state.linePositions.push(pos);
}

export function snapshot(): TrainerState {
  return {
    ...state,
    moveHistory: [...state.moveHistory],
    linePositions: [...state.linePositions],
  };
}
