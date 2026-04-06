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
  detail?: string;
  error?: string;
}

export interface StatsOverview {
  total_games: number;
  analyzed_games: number;
  total_blunders: number;
  [key: string]: unknown;
}
