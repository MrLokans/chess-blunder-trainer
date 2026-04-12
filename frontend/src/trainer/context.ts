import { createContext } from 'preact';
import type { Dispatch } from 'preact/hooks';
export type { PuzzleData } from '../types/api';
import type { PuzzleData } from '../types/api';

type Color = 'white' | 'black';

export interface LinePosition {
  fen: string;
  moveHistory: string[];
}

export type FeedbackType = 'correct' | 'blunder' | 'good' | 'not-quite' | null;
type EmptyStateType = 'no-puzzles' | 'no_games' | 'no_blunders' | 'no_blunders_filtered' | 'analyzing' | null;

export interface TrainerState {
  puzzle: PuzzleData | null;
  submitted: boolean;
  bestRevealed: boolean;
  moveHistory: string[];
  linePositions: LinePosition[];
  lineViewIndex: number;
  animating: boolean;
  boardFlipped: boolean;
  currentStarred: boolean;

  orientation: Color;
  fen: string;

  resultVisible: boolean;
  feedbackType: FeedbackType;
  shortcutsVisible: boolean;
  loading: boolean;
  error: string | null;
  emptyState: EmptyStateType;
}

export type TrainerAction =
  | { type: 'SET_PUZZLE'; puzzle: PuzzleData }
  | { type: 'RESET_FOR_NEW_PUZZLE' }
  | { type: 'SET_SUBMITTED' }
  | { type: 'REVEAL_BEST' }
  | { type: 'PUSH_MOVE'; san: string }
  | { type: 'POP_MOVE' }
  | { type: 'SET_LOADING'; loading: boolean }
  | { type: 'SET_FEEDBACK'; feedbackType: FeedbackType }
  | { type: 'SET_RESULT_VISIBLE'; visible: boolean }
  | { type: 'SET_ORIENTATION'; orientation: Color }
  | { type: 'SET_FEN'; fen: string }
  | { type: 'PUSH_LINE_POSITION'; position: LinePosition }
  | { type: 'SET_LINE_VIEW_INDEX'; index: number }
  | { type: 'CLEAR_LINE_NAVIGATION' }
  | { type: 'SET_ANIMATING'; animating: boolean }
  | { type: 'SET_EMPTY_STATE'; emptyState: EmptyStateType }
  | { type: 'SET_ERROR'; error: string | null }
  | { type: 'TOGGLE_SHORTCUTS' }
  | { type: 'SET_BOARD_FLIPPED'; flipped: boolean }
  | { type: 'SET_STARRED'; starred: boolean };

export const initialState: TrainerState = {
  puzzle: null,
  submitted: false,
  bestRevealed: false,
  moveHistory: [],
  linePositions: [],
  lineViewIndex: -1,
  animating: false,
  boardFlipped: false,
  currentStarred: false,

  orientation: 'white',
  fen: '',

  resultVisible: false,
  feedbackType: null,
  shortcutsVisible: false,
  loading: false,
  error: null,
  emptyState: null,
};

export function trainerReducer(state: TrainerState, action: TrainerAction): TrainerState {
  switch (action.type) {
    case 'SET_PUZZLE':
      return {
        ...state,
        puzzle: action.puzzle,
        submitted: false,
        bestRevealed: false,
        moveHistory: [],
        linePositions: [],
        lineViewIndex: -1,
        animating: false,
        feedbackType: null,
        resultVisible: false,
        loading: false,
        error: null,
        emptyState: null,
      };
    case 'RESET_FOR_NEW_PUZZLE':
      return {
        ...state,
        puzzle: null,
        submitted: false,
        bestRevealed: false,
        moveHistory: [],
        linePositions: [],
        lineViewIndex: -1,
        animating: false,
        feedbackType: null,
        resultVisible: false,
        error: null,
        emptyState: null,
        currentStarred: false,
      };
    case 'SET_SUBMITTED':
      return { ...state, submitted: true };
    case 'REVEAL_BEST':
      return { ...state, bestRevealed: true };
    case 'PUSH_MOVE':
      return { ...state, moveHistory: [...state.moveHistory, action.san] };
    case 'POP_MOVE':
      return { ...state, moveHistory: state.moveHistory.slice(0, -1) };
    case 'SET_LOADING':
      return { ...state, loading: action.loading };
    case 'SET_FEEDBACK':
      return { ...state, feedbackType: action.feedbackType };
    case 'SET_RESULT_VISIBLE':
      return { ...state, resultVisible: action.visible };
    case 'SET_ORIENTATION':
      return { ...state, orientation: action.orientation };
    case 'SET_FEN':
      return { ...state, fen: action.fen };
    case 'PUSH_LINE_POSITION':
      return { ...state, linePositions: [...state.linePositions, action.position] };
    case 'SET_LINE_VIEW_INDEX':
      return { ...state, lineViewIndex: action.index };
    case 'CLEAR_LINE_NAVIGATION':
      return { ...state, linePositions: [], lineViewIndex: -1 };
    case 'SET_ANIMATING':
      return { ...state, animating: action.animating };
    case 'SET_EMPTY_STATE':
      return { ...state, emptyState: action.emptyState };
    case 'SET_ERROR':
      return { ...state, error: action.error };
    case 'TOGGLE_SHORTCUTS':
      return { ...state, shortcutsVisible: !state.shortcutsVisible };
    case 'SET_BOARD_FLIPPED':
      return { ...state, boardFlipped: action.flipped };
    case 'SET_STARRED':
      return { ...state, currentStarred: action.starred };
  }
}

export const TrainerContext = createContext<{
  state: TrainerState;
  dispatch: Dispatch<TrainerAction>;
}>({ state: initialState, dispatch: () => {} });
