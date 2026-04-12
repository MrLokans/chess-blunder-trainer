import { useCallback } from 'preact/hooks';
import type { SyncSettings as SyncSettingsData } from './types';

interface SyncSettingsProps {
  settings: SyncSettingsData;
  syncVisible: boolean;
  analyzeVisible: boolean;
  onChange: (updated: SyncSettingsData) => void;
}

export function SyncSettings({ settings, syncVisible, analyzeVisible, onChange }: SyncSettingsProps) {
  const update = useCallback(<K extends keyof SyncSettingsData>(key: K, value: SyncSettingsData[K]) => {
    onChange({ ...settings, [key]: value });
  }, [settings, onChange]);

  return (
    <>
      <div data-section="sync" class={syncVisible ? '' : 'hidden'}>
        <hr class="section-divider" />
        <h2 class="settings-section-title">{t('settings.auto_sync.title')}</h2>

        <div class="form-group">
          <label class="checkbox-label">
            <input
              type="checkbox"
              checked={settings.auto_sync}
              onChange={() => { update('auto_sync', !settings.auto_sync); }}
              aria-label={t('settings.auto_sync.enable')}
            />
            {t('settings.auto_sync.enable')}
          </label>
          <div class="help-text">{t('settings.auto_sync.help')}</div>
        </div>

        <div class="form-group">
          <label>{t('settings.sync_interval.label')}</label>
          <select
            value={String(settings.sync_interval)}
            onChange={(e) => { update('sync_interval', Number(e.currentTarget.value)); }}
          >
            <option value="6">{t('settings.sync_interval.6h')}</option>
            <option value="12">{t('settings.sync_interval.12h')}</option>
            <option value="24">{t('settings.sync_interval.24h')}</option>
            <option value="48">{t('settings.sync_interval.48h')}</option>
          </select>
        </div>

        <div class="form-group">
          <label>{t('settings.max_games.label')}</label>
          <input
            type="number"
            min={100}
            max={10000}
            value={settings.max_games}
            class="settings-input"
            aria-label={t('settings.max_games.label')}
            onInput={(e) => { update('max_games', Number(e.currentTarget.value)); }}
          />
          <div class="help-text">{t('settings.max_games.help')}</div>
        </div>
      </div>

      <div data-section="analyze" class={analyzeVisible ? '' : 'hidden'}>
        <div class="form-group">
          <label class="checkbox-label">
            <input
              type="checkbox"
              checked={settings.auto_analyze}
              onChange={() => { update('auto_analyze', !settings.auto_analyze); }}
              aria-label={t('settings.auto_analyze.enable')}
            />
            {t('settings.auto_analyze.enable')}
          </label>
          <div class="help-text">{t('settings.auto_analyze.help')}</div>
        </div>
      </div>

      <hr class="section-divider" />
      <h2 class="settings-section-title">{t('settings.training.title')}</h2>
      <div class="form-group">
        <label>{t('settings.spaced_repetition.label')}</label>
        <input
          type="number"
          min={1}
          max={365}
          value={settings.spaced_repetition_days}
          class="settings-input"
          aria-label={t('settings.spaced_repetition.label')}
          onInput={(e) => { update('spaced_repetition_days', Number(e.currentTarget.value)); }}
        />
        <div class="help-text">{t('settings.spaced_repetition.help')}</div>
      </div>
    </>
  );
}
