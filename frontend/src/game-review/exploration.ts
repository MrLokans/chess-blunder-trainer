export interface ExplorationState {
  active: boolean;
  baseFen: string;
  fen: string;
  sans: string[];
}

export const IDLE: ExplorationState = { active: false, baseFen: '', fen: '', sans: [] };

export function begin(baseFen: string): ExplorationState {
  return { active: true, baseFen, fen: baseFen, sans: [] };
}

export function push(s: ExplorationState, fen: string, san: string): ExplorationState {
  return { ...s, active: true, fen, sans: [...s.sans, san] };
}

export function pop(s: ExplorationState, prevFen: string): ExplorationState {
  if (s.sans.length === 0) return s;
  return { ...s, fen: prevFen, sans: s.sans.slice(0, -1) };
}
