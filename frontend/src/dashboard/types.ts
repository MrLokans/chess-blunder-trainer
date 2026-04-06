import type { OpeningItem } from '../shared/opening-group';

export interface DateFilterParams {
  start_date?: string;
  end_date?: string;
  game_types?: string[];
  game_phases?: string[];
}

export type DatePreset = '7d' | '30d' | '90d' | '1y' | 'all';

export interface PhaseEntry {
  phase: string;
  count: number;
  percentage: number;
  avg_cp_loss: number;
}

export interface PhaseData {
  total_blunders: number;
  by_phase: PhaseEntry[];
}

export interface ColorEntry {
  color: string;
  count: number;
  percentage: number;
  avg_cp_loss: number;
}

export interface ColorData {
  total_blunders: number;
  by_color: ColorEntry[];
}

export interface GameTypeEntry {
  game_type: string;
  count: number;
  percentage: number;
}

export interface GameTypeData {
  total_blunders: number;
  by_game_type: GameTypeEntry[];
}

export interface TacticalEntry {
  pattern: string;
  count: number;
  percentage: number;
}

export interface TacticalData {
  total_blunders: number;
  by_pattern: TacticalEntry[];
}

export interface DifficultyEntry {
  difficulty: string;
  count: number;
  percentage: number;
  avg_cp_loss: number;
}

export interface DifficultyData {
  total_blunders: number;
  by_difficulty: DifficultyEntry[];
}

export interface DistributionEntry {
  move_range: string;
  count: number;
}

export interface CollapsePointData {
  avg_collapse_move: number | null;
  median_collapse_move: number | null;
  total_games_with_blunders: number;
  total_games_without_blunders: number;
  distribution: DistributionEntry[];
}

export interface ConversionResilienceData {
  games_with_advantage: number;
  games_converted: number;
  conversion_rate: number;
  games_with_disadvantage: number;
  games_saved: number;
  resilience_rate: number;
}

export interface TrapTop {
  trap_id: string;
  count: number;
}

export interface TrapStat {
  trap_id: string;
  name: string;
}

export interface TrapsData {
  summary: {
    total_sprung: number;
    total_entered: number;
    top_traps?: TrapTop[];
  };
  stats: TrapStat[];
}

export interface GameBreakdownItem {
  source: string;
  username: string;
  total_games: number;
  analyzed_games: number;
  pending_games: number;
}

export interface EcoData {
  total_blunders: number;
  by_opening: OpeningItem[];
}

export interface OverviewData {
  total_games: number;
  analyzed_games: number;
  total_blunders: number;
}

export interface AnalysisStatus {
  status: string;
  progress_current?: number;
  progress_total?: number;
}

export interface DateChartItem {
  date: string;
  game_count: number;
  avg_accuracy: number;
}

export interface HourChartItem {
  hour: number;
  game_count: number;
  avg_accuracy: number;
}
