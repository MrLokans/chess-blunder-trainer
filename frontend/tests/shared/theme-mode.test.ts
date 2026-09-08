import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  LEGACY_DARK_THEME, getThemeMode, migrateLegacyDarkTheme, setThemeMode,
} from '../../src/shared/theme-mode';
import { STORAGE_KEYS } from '../../src/shared/storage-keys';

afterEach(() => {
  localStorage.clear();
  delete window.syncThemeMode;
});

describe('theme mode', () => {
  it('uses system mode without a saved choice', () => {
    expect(getThemeMode()).toBe('system');
  });

  it('migrates an exact legacy dark theme once', () => {
    migrateLegacyDarkTheme(LEGACY_DARK_THEME);
    expect(getThemeMode()).toBe('dark');

    setThemeMode('light');
    migrateLegacyDarkTheme(LEGACY_DARK_THEME);
    expect(localStorage.getItem(STORAGE_KEYS.themeMode)).toBe('light');
  });

  it('keeps custom colors in system mode and records the migration', () => {
    migrateLegacyDarkTheme({ ...LEGACY_DARK_THEME, text: '#F0EDE7' });
    expect(getThemeMode()).toBe('system');
    expect(localStorage.getItem(STORAGE_KEYS.themeModeMigration)).toBe('true');
  });

  it('applies the mode to the document whenever it is stored', () => {
    const syncThemeMode = vi.fn();
    window.syncThemeMode = syncThemeMode;

    migrateLegacyDarkTheme(LEGACY_DARK_THEME);
    expect(syncThemeMode).toHaveBeenCalledTimes(1);

    setThemeMode('system');
    expect(syncThemeMode).toHaveBeenCalledTimes(2);
  });

  it('does not override an explicit mode', () => {
    setThemeMode('light');
    migrateLegacyDarkTheme(LEGACY_DARK_THEME);
    expect(getThemeMode()).toBe('light');
  });
});
