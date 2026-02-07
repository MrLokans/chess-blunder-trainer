import { client } from './api.js';
import { getCurrentTheme, initThemeEditor } from './settings/theme-editor.js';
import { initBoardEditor, saveBoardSettings } from './settings/board-editor.js';

const form = document.getElementById('settingsForm');
const errorAlert = document.getElementById('errorAlert');
const successAlert = document.getElementById('successAlert');
const submitBtn = document.getElementById('submitBtn');
const lichessInput = document.getElementById('lichess');
const chesscomInput = document.getElementById('chesscom');
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

  const lichess = lichessInput.value.trim();
  const chesscom = chesscomInput.value.trim();

  if (!lichess && !chesscom) {
    showError(t('settings.username_error'));
    return;
  }

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
      lichess,
      chesscom,
      auto_sync: autoSync,
      sync_interval: syncInterval,
      max_games: maxGames,
      auto_analyze: autoAnalyze,
      spaced_repetition_days: spacedRepetitionDays,
      theme
    });

    await saveBoardSettings();
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
    const locale = localeSelect.value;
    document.cookie = `locale=${locale};path=/;max-age=${365 * 24 * 3600};SameSite=Lax`;
    client.settings.setLocale(locale).then(() => {
      window.location.href = '/settings';
    }).catch(() => {
      window.location.href = '/settings';
    });
  });
}

const SETTINGS_PAGE_FEATURES = new Set(['auto.sync', 'auto.analyze']);

function initFeatureToggles() {
  let needsReload = false;
  let reloadTimer = null;

  document.querySelectorAll('.feature-toggle').forEach(el => {
    el.addEventListener('change', async () => {
      if (reloadTimer) clearTimeout(reloadTimer);

      try {
        await client.settings.saveFeatures({ [el.dataset.feature]: el.checked });
        window.__features[el.dataset.feature] = el.checked;

        if (SETTINGS_PAGE_FEATURES.has(el.dataset.feature)) {
          needsReload = true;
        }
      } catch (err) {
        el.checked = !el.checked;
        console.error('Failed to save feature toggle:', err);
        return;
      }

      if (needsReload) {
        reloadTimer = setTimeout(() => window.location.reload(), 600);
      }
    });
  });
}

loadSyncSettings();
initBoardEditor();
initFeatureToggles();
