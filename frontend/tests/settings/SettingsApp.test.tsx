import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/preact';
import { SettingsApp } from '../../src/settings/SettingsApp';
import type { SettingsInit } from '../../src/settings/types';

const INIT: SettingsInit = {
  featureGroups: [
    {
      label: 'settings.features.group.automation',
      features: [
        { id: 'auto.sync', label: 'settings.features.auto_sync', enabled: true },
        { id: 'auto.analyze', label: 'settings.features.auto_analyze', enabled: true },
      ],
    },
  ],
  availableLocales: [
    { code: 'en', name: 'English' },
    { code: 'ru', name: 'Russian' },
  ],
  currentLocale: 'en',
  demoMode: false,
};

vi.mock('../../src/shared/api', () => ({
  client: {
    settings: {
      get: vi.fn().mockResolvedValue({
        auto_sync: false, sync_interval: 24, max_games: 1000,
        auto_analyze: true, spaced_repetition_days: 30,
      }),
      save: vi.fn().mockResolvedValue({}),
      getTheme: vi.fn().mockResolvedValue({
        primary: '#4f6d7a', success: '#3d8b6e', error: '#c25450', warning: '#b8860b',
        phase_opening: '#5b8a9a', phase_middlegame: '#9a7b5b', phase_endgame: '#7a5b9a',
        bg: '#f1f5f9', bg_card: '#ffffff', text: '#1e293b', text_muted: '#64748b',
        heatmap_empty: '#ebedf0', heatmap_l1: '#9be9a8', heatmap_l2: '#40c463',
        heatmap_l3: '#30a14e', heatmap_l4: '#216e39',
      }),
      getThemePresets: vi.fn().mockResolvedValue({ presets: [] }),
      getBoard: vi.fn().mockResolvedValue({ piece_set: 'gioco', board_light: '#f0d9b5', board_dark: '#b58863' }),
      saveBoard: vi.fn().mockResolvedValue({}),
      getPieceSets: vi.fn().mockResolvedValue({ piece_sets: [{ id: 'gioco', name: 'Gioco' }] }),
      getBoardColorPresets: vi.fn().mockResolvedValue({ presets: [] }),
      saveFeatures: vi.fn().mockResolvedValue({}),
      setLocale: vi.fn().mockResolvedValue({}),
    },
  },
}));

describe('SettingsApp', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.__features = { 'auto.sync': true, 'auto.analyze': true };
  });

  test('renders the settings page title after loading', async () => {
    render(<SettingsApp init={INIT} />);
    await waitFor(() => {
      expect(screen.getByText(t('settings.title'))).toBeDefined();
    });
  });

  test('renders feature toggles', async () => {
    render(<SettingsApp init={INIT} />);
    await waitFor(() => {
      expect(screen.getByLabelText('settings.features.auto_sync')).toBeDefined();
    });
  });

  test('renders locale selector with options', async () => {
    render(<SettingsApp init={INIT} />);
    await waitFor(() => {
      expect(screen.getByText('English')).toBeDefined();
      expect(screen.getByText('Russian')).toBeDefined();
    });
  });

  test('hides submit button in demo mode', async () => {
    render(<SettingsApp init={{ ...INIT, demoMode: true }} />);
    await waitFor(() => {
      expect(screen.getByText(t('settings.title'))).toBeDefined();
    });
    expect(screen.queryByText(t('settings.save'))).toBeNull();
  });

  test('shows save button when not in demo mode', async () => {
    render(<SettingsApp init={INIT} />);
    await waitFor(() => {
      expect(screen.getByText(t('settings.save'))).toBeDefined();
    });
  });
});
