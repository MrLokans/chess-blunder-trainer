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
    document.getElementById('autoSync').checked = settings.auto_sync;
    document.getElementById('syncInterval').value = String(settings.sync_interval);
    document.getElementById('maxGames').value = String(settings.max_games);
    document.getElementById('autoAnalyze').checked = settings.auto_analyze;
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

  const autoSync = document.getElementById('autoSync').checked;
  const syncInterval = document.getElementById('syncInterval').value;
  const maxGames = document.getElementById('maxGames').value;
  const autoAnalyze = document.getElementById('autoAnalyze').checked;
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
      window.location.reload();
    }).catch(() => {
      window.location.reload();
    });
  });
}

loadSyncSettings();
initBoardEditor();
