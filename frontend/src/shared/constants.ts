export const GAME_TYPES = ['bullet', 'blitz', 'rapid', 'classical'] as const;
export const GAME_PHASES = ['opening', 'middlegame', 'endgame'] as const;
export const DIFFICULTIES = ['easy', 'medium', 'hard'] as const;

// Trainer filter values, with the label the stats API reports for the same pattern.
export const TACTICAL_PATTERNS = [
  { value: 'fork', key: 'trainer.filters.tactical_fork', statsName: 'Fork' },
  { value: 'pin', key: 'trainer.filters.tactical_pin', statsName: 'Pin' },
  { value: 'hanging_piece', key: 'trainer.filters.tactical_hanging', statsName: 'Hanging Piece' },
  { value: 'skewer', key: 'trainer.filters.tactical_skewer', statsName: 'Skewer' },
  { value: 'discovered_attack', key: 'trainer.filters.tactical_discovery', statsName: 'Discovered Attack' },
] as const;

export type GameType = typeof GAME_TYPES[number];
export type GamePhase = typeof GAME_PHASES[number];
export type Difficulty = typeof DIFFICULTIES[number];
