import type { ThemeColors } from '../types/settings';
import { STORAGE_KEYS } from './storage-keys';

export type ThemeMode = 'system' | 'light' | 'dark';

export const LEGACY_DARK_THEME: ThemeColors = {
  primary: '#5B8FD4', success: '#4AAF6A', error: '#E05050', warning: '#F2C12E',
  phase_opening: '#5B8FD4', phase_middlegame: '#F2C12E', phase_endgame: '#8A8A8A',
  bg: '#1A1A1A', bg_card: '#2A2A2A', text: '#F0EDE6', text_muted: '#8A8A80',
  heatmap_empty: '#2A2A2A', heatmap_l1: '#1A4A2A', heatmap_l2: '#2A6A3A',
  heatmap_l3: '#3A8A4A', heatmap_l4: '#4AAF6A',
};

export function getThemeMode(): ThemeMode {
  const mode = localStorage.getItem(STORAGE_KEYS.themeMode);
  return mode === 'light' || mode === 'dark' ? mode : 'system';
}

export function setThemeMode(mode: ThemeMode): void {
  if (mode === 'system') localStorage.removeItem(STORAGE_KEYS.themeMode);
  else localStorage.setItem(STORAGE_KEYS.themeMode, mode);
}

export function migrateLegacyDarkTheme(theme: ThemeColors): void {
  if (localStorage.getItem(STORAGE_KEYS.themeModeMigration) !== null) return;
  const hasMode = getThemeMode() !== 'system';
  const matches = (Object.keys(LEGACY_DARK_THEME) as Array<keyof ThemeColors>).every(
    key => theme[key].toLowerCase() === LEGACY_DARK_THEME[key].toLowerCase(),
  );
  if (!hasMode && matches) setThemeMode('dark');
  localStorage.setItem(STORAGE_KEYS.themeModeMigration, 'true');
}
