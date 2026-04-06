export interface EventMap {
  'puzzle:loaded': { fen: string; moveIndex: number; gameId: string };
  'puzzle:solved': { correct: boolean };
  'puzzle:revealed': undefined;
  'board:move': { from: string; to: string; san: string };
  'board:reset': undefined;
  'filter:changed': { type: string; values: string[] };
  'ws:connected': undefined;
  'ws:disconnected': undefined;
  [key: string]: unknown;
}
