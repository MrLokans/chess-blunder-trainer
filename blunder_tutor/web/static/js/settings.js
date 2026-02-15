import { client } from './api.js';
import { getCurrentTheme, initThemeEditor } from './settings/theme-editor.js';
import { initBoardEditor, saveBoardSettings } from './settings/board-editor.js';

const form = document.getElementById('settingsForm');
const errorAlert = document.getElementById('errorAlert');
const successAlert = document.getElementById('successAlert');
const submitBtn = document.getElementById('submitBtn');
const localeSelect = document.getElementById('localeSelect');

function showError(message) {
  errorAlert.textContent = message;
  errorAlert.classList.add('visible');
  successAlert.classList.remove('visible');
}

function showSuccess(message) {
  successAlert.textContent = message;
  successAlert.classList.add('visible');
  errorAlert.classList.remove('visible');
}

function hideAlerts() {
  errorAlert.classList.remove('visible');
  successAlert.classList.remove('visible');
}

async function loadSyncSettings() {
  try {
    await initThemeEditor();

    const settings = await client.settings.get();
    const autoSyncEl = document.getElementById('autoSync');
    const syncIntervalEl = document.getElementById('syncInterval');
    const maxGamesEl = document.getElementById('maxGames');
    const autoAnalyzeEl = document.getElementById('autoAnalyze');
    if (autoSyncEl) autoSyncEl.checked = settings.auto_sync;
    if (syncIntervalEl) syncIntervalEl.value = String(settings.sync_interval);
    if (maxGamesEl) maxGamesEl.value = String(settings.max_games);
    if (autoAnalyzeEl) autoAnalyzeEl.checked = settings.auto_analyze;
    document.getElementById('spacedRepetitionDays').value = String(settings.spaced_repetition_days);
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideAlerts();

  const autoSyncEl = document.getElementById('autoSync');
  const syncIntervalEl = document.getElementById('syncInterval');
  const maxGamesInputEl = document.getElementById('maxGames');
  const autoAnalyzeEl = document.getElementById('autoAnalyze');
  const autoSync = autoSyncEl ? autoSyncEl.checked : false;
  const syncInterval = syncIntervalEl ? syncIntervalEl.value : '24';
  const maxGames = maxGamesInputEl ? maxGamesInputEl.value : '1000';
  const autoAnalyze = autoAnalyzeEl ? autoAnalyzeEl.checked : true;
  const spacedRepetitionDays = document.getElementById('spacedRepetitionDays').value;

  submitBtn.disabled = true;
  submitBtn.textContent = 'Saving...';

  try {
    const theme = getCurrentTheme();

    await client.settings.save({
      auto_sync: autoSync,
      sync_interval: syncInterval,
      max_games: maxGames,
      auto_analyze: autoAnalyze,
      spaced_repetition_days: spacedRepetitionDays,
      theme
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
    submitBtn.disabled = false;
    submitBtn.textContent = t('settings.save');
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

const FEATURE_SECTION_MAP = {
  'auto.sync': 'autoSyncSection',
  'auto.analyze': 'autoAnalyzeSection',
};

function initFeatureToggles() {
  document.querySelectorAll('.feature-toggle').forEach(el => {
    el.addEventListener('change', async () => {
      const featureId = el.dataset.feature;
      const newValue = el.checked;

      try {
        await client.settings.saveFeatures({ [featureId]: newValue });
        window.__features[featureId] = newValue;

        const sectionId = FEATURE_SECTION_MAP[featureId];
        if (sectionId) {
          const section = document.getElementById(sectionId);
          if (section) {
            section.style.display = newValue ? '' : 'none';
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
