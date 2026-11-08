import { STORAGE_KEYS } from './storage-keys';

interface BoardDisplayOptionSpec {
  key: string;
  fallback: boolean;
  label: string;
  feature?: string;
}

export const BOARD_DISPLAY_OPTIONS = {
  showArrows: { key: STORAGE_KEYS.trainerShowArrows, fallback: true, label: 'trainer.toggle.show_arrows' },
  showThreats: { key: STORAGE_KEYS.trainerShowThreats, fallback: false, label: 'trainer.toggle.show_threats', feature: 'trainer.threats' },
  showTactics: { key: STORAGE_KEYS.trainerShowTactics, fallback: true, label: 'trainer.toggle.show_tactics', feature: 'trainer.tactics' },
  showCoordinates: { key: STORAGE_KEYS.trainerShowCoordinates, fallback: true, label: 'trainer.toggle.show_coordinates' },
} satisfies Record<string, BoardDisplayOptionSpec>;

export type BoardDisplayOption = keyof typeof BOARD_DISPLAY_OPTIONS;

export function loadBoardDisplay(option: BoardDisplayOption): boolean {
  const { key, fallback } = BOARD_DISPLAY_OPTIONS[option];
  const raw = localStorage.getItem(key);
  return raw === null ? fallback : raw === 'true';
}

export function saveBoardDisplay(option: BoardDisplayOption, enabled: boolean): void {
  localStorage.setItem(BOARD_DISPLAY_OPTIONS[option].key, String(enabled));
}
