import { client } from '../shared/api';
import { getCurrentTheme, initThemeEditor } from './theme-editor';
import { initBoardEditor, saveBoardSettings } from './board-editor';
import { initDropdowns } from '../shared/dropdown';

const form = document.getElementById('settingsForm') as HTMLFormElement | null;
const errorAlert = document.getElementById('errorAlert');
const successAlert = document.getElementById('successAlert');
const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement | null;
const localeSelect = document.getElementById('localeSelect') as HTMLSelectElement | null;

function showError(message: string): void {
  if (errorAlert) {
    errorAlert.textContent = message;
    errorAlert.classList.add('visible');
  }
  successAlert?.classList.remove('visible');
}

function showSuccess(message: string): void {
  if (successAlert) {
    successAlert.textContent = message;
    successAlert.classList.add('visible');
  }
  errorAlert?.classList.remove('visible');
}

function hideAlerts(): void {
  errorAlert?.classList.remove('visible');
  successAlert?.classList.remove('visible');
}

interface SyncSettings {
  auto_sync: boolean;
  sync_interval: number;
  max_games: number;
  auto_analyze: boolean;
  spaced_repetition_days: number;
}

async function loadSyncSettings(): Promise<void> {
  try {
    await initThemeEditor();

    const settings = await client.settings.get() as SyncSettings;
    const autoSyncEl = document.getElementById('autoSync') as HTMLInputElement | null;
    const syncIntervalEl = document.getElementById('syncInterval') as HTMLInputElement | null;
    const maxGamesEl = document.getElementById('maxGames') as HTMLInputElement | null;
    const autoAnalyzeEl = document.getElementById('autoAnalyze') as HTMLInputElement | null;
    if (autoSyncEl) autoSyncEl.checked = settings.auto_sync;
    if (syncIntervalEl) syncIntervalEl.value = String(settings.sync_interval);
    if (maxGamesEl) maxGamesEl.value = String(settings.max_games);
    if (autoAnalyzeEl) autoAnalyzeEl.checked = settings.auto_analyze;
    const spacedEl = document.getElementById('spacedRepetitionDays') as HTMLInputElement | null;
    if (spacedEl) spacedEl.value = String(settings.spaced_repetition_days);
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideAlerts();

  const autoSyncEl = document.getElementById('autoSync') as HTMLInputElement | null;
  const syncIntervalEl = document.getElementById('syncInterval') as HTMLInputElement | null;
  const maxGamesInputEl = document.getElementById('maxGames') as HTMLInputElement | null;
  const autoAnalyzeEl = document.getElementById('autoAnalyze') as HTMLInputElement | null;
  const autoSync = autoSyncEl ? autoSyncEl.checked : false;
  const syncInterval = syncIntervalEl ? syncIntervalEl.value : '24';
  const maxGames = maxGamesInputEl ? maxGamesInputEl.value : '1000';
  const autoAnalyze = autoAnalyzeEl ? autoAnalyzeEl.checked : true;
  const spacedEl = document.getElementById('spacedRepetitionDays') as HTMLInputElement | null;
  const spacedRepetitionDays = spacedEl?.value ?? '7';

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = 'Saving...';
  }

  try {
    const theme = getCurrentTheme();

    await client.settings.save({
      auto_sync: autoSync,
      sync_interval: syncInterval,
      max_games: maxGames,
      auto_analyze: autoAnalyze,
      spaced_repetition_days: spacedRepetitionDays,
      theme,
    });

    trackEvent('Theme Changed', { theme: 'custom' });

    await saveBoardSettings();
    trackEvent('Board Style Changed', { piece_set: 'saved' });
    localStorage.setItem('theme', JSON.stringify(theme));

    showSuccess(t('settings.saved'));
    setTimeout(() => {
      window.location.href = '/';
    }, 1500);
  } catch (err) {
    showError(t('settings.save_error'));
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('settings.save');
    }
    console.error(err);
  }
});

if (localeSelect) {
  localeSelect.addEventListener('change', () => {
    trackEvent('Locale Changed', { locale: localeSelect.value });
    client.settings.setLocale(localeSelect.value).then(() => {
      window.location.reload();
    }).catch(() => {
      window.location.reload();
    });
  });
}

const FEATURE_SECTION_MAP: Record<string, string> = {
  'auto.sync': 'autoSyncSection',
  'auto.analyze': 'autoAnalyzeSection',
};

function initFeatureToggles(): void {
  document.querySelectorAll<HTMLInputElement>('.feature-toggle').forEach(el => {
    el.addEventListener('change', async () => {
      const featureId = el.dataset.feature;
      if (!featureId) return;
      const newValue = el.checked;

      try {
        await client.settings.saveFeatures({ [featureId]: newValue });
        window.__features[featureId] = newValue;

        const sectionId = FEATURE_SECTION_MAP[featureId];
        if (sectionId) {
          const section = document.getElementById(sectionId);
          if (section) {
            section.classList.toggle('hidden', !newValue);
          }
        }
      } catch (err) {
        el.checked = !newValue;
        console.error('Failed to save feature toggle:', err);
      }
    });
  });
}

loadSyncSettings();
initBoardEditor();
initFeatureToggles();
initDropdowns();
