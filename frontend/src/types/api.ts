export interface BlunderPuzzle {
  game_id: string;
  fen: string;
  ply: number;
  san: string;
  best_move_san: string;
  best_line_san: string[];
  eval_before: number;
  eval_after: number;
  cp_loss: number;
  player_color: 'white' | 'black';
  source: string;
  opponent: string;
  date: string;
  game_phase: string;
  tactical_pattern: string | null;
  explanation_blunder: string | null;
  explanation_best: string | null;
  game_url: string | null;
  difficulty: string;
}

export interface ApiErrorResponse {
  // FastAPI returns `detail` as a string for HTTPException(detail="...") and
  // as a dict (e.g. {"error": "already_tracked", "profile_id": 1}) when the
  // handler raises with a structured payload. The shared error extractor
  // unwraps both shapes.
  detail?: string | Record<string, unknown>;
  error?: string;
}

export type JobState = 'idle' | 'running' | 'completed' | 'failed';

export interface JobStatus {
  status: JobState;
  job_id?: string;
  progress_current?: number;
  progress_total?: number;
}

export interface StatsOverview {
  total_games: number;
  analyzed_games: number;
  total_blunders: number;
  [key: string]: unknown;
}

export interface ImportResult {
  eco_code?: string;
  eco_name?: string;
  total_moves?: number;
  blunders?: number;
  mistakes?: number;
  inaccuracies?: number;
}

export interface ImportStartResponse {
  success: boolean;
  job_id?: string;
  errors?: string[];
}

export interface JobStatusResponse {
  status: JobState;
  result?: ImportResult;
  error_message?: string;
}

// Puzzle / trainer types

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
  tactical_squares: string[] | null;
  explanation_blunder: string | null;
  explanation_best: string | null;
  game_url: string | null;
  difficulty: string;
  pre_move_uci: string | null;
  pre_move_fen: string | null;
  best_move_eval: number | null;
}

export interface SubmitMovePayload {
  move: string;
  fen: string;
  game_id: string;
  ply: number;
  blunder_uci: string;
  blunder_san: string;
  best_move_uci: string;
  best_move_san: string;
  best_line: string[];
  player_color: string;
  eval_after: number;
  best_move_eval: number | null;
}

export interface SubmitMoveResponse {
  is_best: boolean;
  is_blunder: boolean;
  user_san: string;
  user_eval: number;
  user_eval_display: string;
  user_uci: string;
}

// Game review types

export interface ReviewMove {
  san: string;
  move_number: number;
  player: string;
  ply: number;
  eval_after: number;
  classification?: string;
}

export interface ReviewGame {
  username?: string;
  white: string;
  black: string;
  result?: string;
  game_url?: string;
}

export interface ReviewData {
  moves: ReviewMove[];
  game: ReviewGame;
  analyzed: boolean;
}

// Starred types

export interface StarredItem {
  game_id: string;
  ply: number;
  san?: string;
  date?: string;
  white?: string;
  black?: string;
  cp_loss?: number | null;
  game_phase?: number;
  note?: string;
}

// Trap types

export interface TrapStat {
  trap_id: string;
  name: string;
  category: string;
  entered: number;
  sprung: number;
  executed: number;
  last_seen?: string;
}

export interface TrapSummary {
  total_sprung: number;
  total_entered: number;
  total_executed: number;
  games_with_traps: number;
  top_traps?: Array<{ trap_id: string; count: number }>;
}

export interface TrapCatalogEntry {
  id: string;
  name: string;
}

export interface TrapDetail {
  name: string;
  victim_side: string;
  trap_san?: string[][];
  refutation_san?: string[];
  mistake_san?: string;
  refutation_note?: string;
  refutation_move?: string;
  recognition_tip?: string;
}

export interface TrapHistory {
  white: string;
  black: string;
  result: string;
  date?: string;
  game_url?: string;
  match_type: string;
}

export interface TrapDetailData {
  trap: TrapDetail | null;
  history: TrapHistory[];
}

export interface TrapStatsResponse {
  stats: TrapStat[];
  summary: TrapSummary;
}

// Setup types

export interface SetupPayload {
  lichess: string;
  chesscom: string;
}
