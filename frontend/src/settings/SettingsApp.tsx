import { useState, useCallback } from 'preact/hooks';
import { client } from '../shared/api';
import { STORAGE_KEYS } from '../shared/storage-keys';
import { useAsyncData } from '../hooks/useAsyncData';
import { AsyncBoundary } from '../components/feedback/AsyncBoundary';
import { Alert } from '../components/feedback/Alert';
import { Button } from '../components/primitives/Button';
import { Card } from '../components/layout/Card';
import { PageHeader } from '../components/layout/PageHeader';
import { FeatureToggles } from './FeatureToggles';
import { SyncSettings } from './SyncSettings';
import { ThemeEditor } from './ThemeEditor';
import { BoardEditor } from './BoardEditor';
import { CacheManagement } from './CacheManagement';
import type {
  SettingsInit, SyncSettings as SyncSettingsData,
  ThemeColors, ThemePreset, PieceSet, BoardColorPreset,
  BoardSettings as BoardSettingsData,
} from './types';

interface SettingsAppProps {
  init: SettingsInit;
}

interface SettingsBundle {
  syncSettings: SyncSettingsData;
  theme: ThemeColors;
  themePresets: ThemePreset[];
  boardSettings: BoardSettingsData;
  pieceSets: PieceSet[];
  boardColorPresets: BoardColorPreset[];
}

const FEATURE_SECTION_MAP: Record<string, string> = {
  'auto.sync': 'sync',
  'auto.analyze': 'analyze',
};

export function SettingsApp({ init }: SettingsAppProps) {
  const state = useAsyncData<SettingsBundle>(async () => {
    const [settings, themeData, presetsData, boardData, pieceSetsData, colorPresetsData] =
      await Promise.all([
        client.settings.get(),
        client.settings.getTheme(),
        client.settings.getThemePresets(),
        client.settings.getBoard(),
        client.settings.getPieceSets(),
        client.settings.getBoardColorPresets(),
      ]);
    return {
      syncSettings: settings,
      theme: themeData,
      themePresets: presetsData.presets,
      boardSettings: boardData,
      pieceSets: pieceSetsData.piece_sets,
      boardColorPresets: colorPresetsData.presets,
    };
  }, []);

  return (
    <AsyncBoundary state={state}>
      {(bundle) => <SettingsForm init={init} bundle={bundle} />}
    </AsyncBoundary>
  );
}

interface SettingsFormProps {
  init: SettingsInit;
  bundle: SettingsBundle;
}

function SettingsForm({ init, bundle }: SettingsFormProps) {
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);

  const [syncSettings, setSyncSettings] = useState(bundle.syncSettings);
  const [theme, setTheme] = useState(bundle.theme);
  const [boardSettings, setBoardSettings] = useState(bundle.boardSettings);
  const { themePresets, pieceSets, boardColorPresets } = bundle;

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

  return (
    <Card border="top">
      <PageHeader title={t('settings.title')} subtitle={t('settings.subtitle')} />

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
          {/* eslint-disable-next-line no-restricted-syntax -- navigational anchor, not a <button>; <Button> renders only <button> */}
          <a class="btn btn-secondary" href="/">{t('common.cancel')}</a>
          {!init.demoMode && (
            <Button type="submit" variant="primary" disabled={saving}>
              {saving ? t('settings.saving') : t('settings.save')}
            </Button>
          )}
        </div>
      </form>

      {!init.demoMode && <CacheManagement />}
    </Card>
  );
}
