import { useState, useEffect, useCallback } from 'preact/hooks';
import { client } from '../shared/api';
import { STORAGE_KEYS } from '../shared/storage-keys';
import { Alert } from '../components/Alert';
import { FeatureToggles } from './FeatureToggles';
import { SyncSettings } from './SyncSettings';
import { ThemeEditor } from './ThemeEditor';
import { BoardEditor } from './BoardEditor';
import type {
  SettingsInit, SyncSettings as SyncSettingsData,
  ThemeColors, ThemePreset, PieceSet, BoardColorPreset,
} from './types';

interface SettingsAppProps {
  init: SettingsInit;
}

const FEATURE_SECTION_MAP: Record<string, string> = {
  'auto.sync': 'sync',
  'auto.analyze': 'analyze',
};

export function SettingsApp({ init }: SettingsAppProps) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);

  const [syncSettings, setSyncSettings] = useState<SyncSettingsData>({
    auto_sync: false, sync_interval: 24, max_games: 1000,
    auto_analyze: true, spaced_repetition_days: 30,
  });
  const [theme, setTheme] = useState<ThemeColors | null>(null);
  const [themePresets, setThemePresets] = useState<ThemePreset[]>([]);
  const [boardSettings, setBoardSettings] = useState({
    piece_set: 'gioco', board_light: '#f0d9b5', board_dark: '#b58863',
  });
  const [pieceSets, setPieceSets] = useState<PieceSet[]>([]);
  const [boardColorPresets, setBoardColorPresets] = useState<BoardColorPreset[]>([]);

  const [sectionVisibility, setSectionVisibility] = useState<Record<string, boolean>>(() => {
    const vis: Record<string, boolean> = {};
    for (const group of init.featureGroups) {
      for (const f of group.features) {
        const section = FEATURE_SECTION_MAP[f.id];
        if (section) vis[section] = f.enabled;
      }
    }
    return vis;
  });

  useEffect(() => {
    async function load() {
      try {
        const [settings, themeData, presetsData, boardData, pieceSetsData, colorPresetsData] =
          await Promise.all([
            client.settings.get(),
            client.settings.getTheme(),
            client.settings.getThemePresets(),
            client.settings.getBoard(),
            client.settings.getPieceSets(),
            client.settings.getBoardColorPresets(),
          ]);

        setSyncSettings(settings);
        setTheme(themeData);
        setThemePresets(presetsData.presets);
        setBoardSettings(boardData);
        setPieceSets(pieceSetsData.piece_sets);
        setBoardColorPresets(colorPresetsData.presets);
      } catch (err) {
        console.error('Failed to load settings:', err);
        setMessage({ type: 'error', text: t('settings.load_error') });
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  const handleFeatureChanged = useCallback((featureId: string, enabled: boolean) => {
    const section = FEATURE_SECTION_MAP[featureId];
    if (section) {
      setSectionVisibility(prev => ({ ...prev, [section]: enabled }));
    }
  }, []);

  const handleLocaleChange = useCallback((locale: string) => {
    trackEvent('Locale Changed', { locale });
    client.settings.setLocale(locale).then(() => {
      window.location.reload();
    }).catch(() => {
      window.location.reload();
    });
  }, []);

  const handleSubmit = useCallback(async () => {
    if (!theme) return;
    setMessage(null);
    setSaving(true);

    try {
      await client.settings.save({ ...syncSettings, theme });
      trackEvent('Theme Changed', { theme: 'custom' });

      await client.settings.saveBoard(boardSettings);
      trackEvent('Board Style Changed', { piece_set: boardSettings.piece_set });

      localStorage.setItem(STORAGE_KEYS.theme, JSON.stringify(theme));
      setMessage({ type: 'success', text: t('settings.saved') });
      setTimeout(() => { window.location.href = '/'; }, 1500);
    } catch {
      setMessage({ type: 'error', text: t('settings.save_error') });
      setSaving(false);
    }
  }, [syncSettings, theme, boardSettings]);

  if (loading || !theme) return null;

  return (
    <div class="card">
      <h2>{t('settings.title')}</h2>
      <p class="subtitle">{t('settings.subtitle')}</p>

      <Alert type={message?.type ?? 'success'} message={message?.text ?? null} />

      <form onSubmit={(e) => { e.preventDefault(); void handleSubmit(); }}>
        <h2 class="settings-section-title">{t('settings.locale.label')}</h2>
        <div class="form-group">
          <label>{t('settings.locale.label')}</label>
          <select
            value={init.currentLocale}
            onChange={(e) => { handleLocaleChange(e.currentTarget.value); }}
          >
            {init.availableLocales.map(loc => (
              <option key={loc.code} value={loc.code}>{loc.name}</option>
            ))}
          </select>
          <div class="help-text">{t('settings.locale.description')}</div>
        </div>

        <hr class="section-divider" />

        <h2 class="settings-section-title mb-2">{t('settings.features.title')}</h2>
        <p class="help-text mb-4">{t('settings.features.subtitle')}</p>

        <FeatureToggles
          groups={init.featureGroups}
          onSave={(flags) => client.settings.saveFeatures(flags)}
          onFeatureChanged={handleFeatureChanged}
        />

        <SyncSettings
          settings={syncSettings}
          syncVisible={sectionVisibility['sync'] ?? false}
          analyzeVisible={sectionVisibility['analyze'] ?? false}
          onChange={setSyncSettings}
        />

        <hr class="section-divider" />

        <BoardEditor
          pieceSets={pieceSets}
          colorPresets={boardColorPresets}
          settings={boardSettings}
          onChange={setBoardSettings}
        />

        <hr class="section-divider" />

        <h2 class="settings-section-title">{t('settings.theme.title')}</h2>
        <p class="help-text mb-4">{t('settings.theme.description')}</p>

        <ThemeEditor
          theme={theme}
          presets={themePresets}
          onChange={setTheme}
        />

        <div class="btn-row mt-8">
          <a class="btn btn-secondary" href="/">{t('common.cancel')}</a>
          {!init.demoMode && (
            <button type="submit" class="btn btn-primary" disabled={saving}>
              {saving ? t('settings.saving') : t('settings.save')}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
