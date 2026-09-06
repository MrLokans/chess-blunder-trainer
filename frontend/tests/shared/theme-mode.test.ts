import { afterEach, describe, expect, it } from 'vitest';
import {
  LEGACY_DARK_THEME, getThemeMode, migrateLegacyDarkTheme, setThemeMode,
} from '../../src/shared/theme-mode';
import { STORAGE_KEYS } from '../../src/shared/storage-keys';

afterEach(() => {
  localStorage.clear();
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

  it('does not override an explicit mode', () => {
    setThemeMode('light');
    migrateLegacyDarkTheme(LEGACY_DARK_THEME);
    expect(getThemeMode()).toBe('light');
  });
});
