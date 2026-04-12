export const GAME_TYPES = ['bullet', 'blitz', 'rapid', 'classical'] as const;
export const GAME_PHASES = ['opening', 'middlegame', 'endgame'] as const;
export const DIFFICULTIES = ['easy', 'medium', 'hard'] as const;

export type GameType = typeof GAME_TYPES[number];
export type GamePhase = typeof GAME_PHASES[number];
export type Difficulty = typeof DIFFICULTIES[number];
