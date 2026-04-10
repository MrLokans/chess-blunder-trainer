export interface SyncSettings {
  auto_sync: boolean;
  sync_interval: number;
  max_games: number;
  auto_analyze: boolean;
  spaced_repetition_days: number;
}

export const THEME_COLOR_KEYS = [
  'primary', 'success', 'error', 'warning',
  'phase_opening', 'phase_middlegame', 'phase_endgame',
  'bg', 'bg_card', 'text', 'text_muted',
  'heatmap_empty', 'heatmap_l1', 'heatmap_l2', 'heatmap_l3', 'heatmap_l4',
] as const;

export type ThemeColorKey = typeof THEME_COLOR_KEYS[number];

export type ThemeColors = Record<ThemeColorKey, string>;

export interface ThemePreset {
  id: string;
  name: string;
  colors: ThemeColors;
}

export interface PieceSet {
  id: string;
  name: string;
}

export interface BoardColorPreset {
  id: string;
  name: string;
  light: string;
  dark: string;
}

export interface BoardSettings {
  piece_set: string;
  board_light: string;
  board_dark: string;
}

export interface FeatureGroup {
  label: string;
  features: Array<{ id: string; label: string; enabled: boolean }>;
}

export interface SettingsInit {
  featureGroups: FeatureGroup[];
  availableLocales: Array<{ code: string; name: string }>;
  currentLocale: string;
  demoMode: boolean;
}
