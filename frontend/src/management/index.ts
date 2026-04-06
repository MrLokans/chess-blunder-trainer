import { WebSocketClient } from '../shared/websocket-client';
import { ProgressTracker } from '../shared/progress-tracker';
import { JobCard } from '../shared/job-card';
import type { JobProgressData, JobStatusData } from '../shared/job-card';
import { loadConfiguredUsernames } from '../shared/usernames';
import { client } from '../shared/api';
import { debounce } from '../shared/debounce';
import { initDropdowns } from '../shared/dropdown';

initDropdowns();

const wsClient = new WebSocketClient();

let currentJobId: string | null = null;
let configuredUsernames: Record<string, string> = {};

const STORAGE_KEYS = {
  source: 'blunder_import_source',
  username: 'blunder_import_username',
  maxGames: 'blunder_import_maxGames',
} as const;

const APP_STORAGE_KEYS = [
  STORAGE_KEYS.source,
  STORAGE_KEYS.username,
  STORAGE_KEYS.maxGames,
  'blunder-tutor-phase-filters',
  'blunder-tutor-game-type-filters',
  'blunder-tutor-difficulty-filters',
  'blunder-tutor-tactical-filter',
  'blunder-tutor-color-filter',
  'blunder-tutor-filters-collapsed',
  'dashboard-game-type-filters',
  'blunder-tutor-play-full-line',
];

function clearAppLocalStorage(): void {
  APP_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
}

async function loadEngineStatus(): Promise<void> {
  const container = document.getElementById('engineStatus');
  if (!container) return;
  try {
    const data = await client.system.engineStatus() as { available: boolean; name?: string; path?: string };

    if (data.available) {
      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--success);"></span>
          <span style="font-weight: 600; color: var(--success);">${t('management.engine.available')}</span>
        </div>
        <table style="font-size: 0.875rem; color: var(--text-muted);">
          <tr><td style="padding-right: 16px;">${t('management.engine.name')}</td><td style="font-family: monospace;">${data.name || 'Unknown'}</td></tr>
          <tr><td style="padding-right: 16px;">${t('management.engine.path')}</td><td style="font-family: monospace;">${data.path || 'Unknown'}</td></tr>
        </table>
      `;
    } else {
      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--error);"></span>
          <span style="font-weight: 600; color: var(--error);">${t('management.engine.unavailable')}</span>
        </div>
        <p style="color: var(--text-muted); font-size: 0.875rem;">
          ${t('management.engine.path')} <code>${data.path || t('management.engine.not_configured')}</code><br>
          ${t('management.engine.install_hint')}
        </p>
      `;
    }
  } catch (err) {
    container.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--error);"></span>
        <span style="color: var(--error);">${t('management.engine.load_failed', { error: (err as Error).message })}</span>
      </div>
    `;
    console.error('Failed to load engine status:', err);
  }
}

loadEngineStatus();

function refreshJobsTable(): void {
  htmx.trigger(document.body, 'jobsRefresh');
}

function showMessage(elementId: string, type: string, text: string): void {
  const el = document.getElementById(elementId);
  if (!el) return;
  el.className = 'message ' + type;
  el.textContent = text;
  el.classList.remove('hidden');
  setTimeout(() => { el.classList.add('hidden'); }, 5000);
}

function prefillUsername(source: string): void {
  const usernameInput = document.getElementById('username') as HTMLInputElement | null;
  if (!usernameInput) return;
  const currentValue = usernameInput.value.trim();

  if (!currentValue && source) {
    if (source === 'lichess' && configuredUsernames.lichess_username) {
      usernameInput.value = configuredUsernames.lichess_username;
    } else if (source === 'chesscom' && configuredUsernames.chesscom_username) {
      usernameInput.value = configuredUsernames.chesscom_username;
    }
  }
}

function saveFormValues(): void {
  const sourceEl = document.getElementById('source') as HTMLSelectElement | null;
  const usernameEl = document.getElementById('username') as HTMLInputElement | null;
  const maxGamesEl = document.getElementById('maxGames') as HTMLInputElement | null;
  if (sourceEl) localStorage.setItem(STORAGE_KEYS.source, sourceEl.value);
  if (usernameEl) localStorage.setItem(STORAGE_KEYS.username, usernameEl.value);
  if (maxGamesEl) localStorage.setItem(STORAGE_KEYS.maxGames, maxGamesEl.value);
}

function restoreFormValues(): void {
  const savedSource = localStorage.getItem(STORAGE_KEYS.source);
  const savedUsername = localStorage.getItem(STORAGE_KEYS.username);
  const savedMaxGames = localStorage.getItem(STORAGE_KEYS.maxGames);

  const sourceEl = document.getElementById('source') as HTMLSelectElement | null;
  const usernameEl = document.getElementById('username') as HTMLInputElement | null;
  const maxGamesEl = document.getElementById('maxGames') as HTMLInputElement | null;

  if (savedSource && sourceEl) sourceEl.value = savedSource;
  if (savedUsername && usernameEl) usernameEl.value = savedUsername;
  if (savedMaxGames && maxGamesEl) maxGamesEl.value = savedMaxGames;
}

async function initialize(): Promise<void> {
  configuredUsernames = await loadConfiguredUsernames();
  restoreFormValues();

  const sourceEl = document.getElementById('source') as HTMLSelectElement | null;
  const usernameEl = document.getElementById('username') as HTMLInputElement | null;
  const restoredSource = sourceEl?.value;
  if (restoredSource && usernameEl && !usernameEl.value) {
    prefillUsername(restoredSource);
  }
}

const usernameStatus = document.getElementById('usernameStatus');
let importUsernameValid: boolean | null = null;

function setUsernameFieldStatus(state: string | null): void {
  if (!usernameStatus) return;
  usernameStatus.className = 'field-validation';
  usernameStatus.textContent = '';
  if (state === 'checking') {
    usernameStatus.classList.add('checking');
    usernameStatus.textContent = t('setup.validating');
  } else if (state === 'valid') {
    usernameStatus.classList.add('valid');
    usernameStatus.textContent = t('setup.username_valid');
  } else if (state === 'invalid') {
    usernameStatus.classList.add('invalid');
    usernameStatus.textContent = t('setup.username_invalid');
  }
}

async function validateImportUsername(): Promise<void> {
  const sourceEl = document.getElementById('source') as HTMLSelectElement | null;
  const usernameEl = document.getElementById('username') as HTMLInputElement | null;
  const source = sourceEl?.value ?? '';
  const username = usernameEl?.value.trim() ?? '';
  if (!source || !username) {
    importUsernameValid = null;
    setUsernameFieldStatus(null);
    return;
  }
  setUsernameFieldStatus('checking');
  try {
    const result = await client.setup.validateUsername(source, username) as { valid: boolean };
    if ((document.getElementById('username') as HTMLInputElement | null)?.value.trim() !== username) return;
    importUsernameValid = result.valid;
    setUsernameFieldStatus(result.valid ? 'valid' : 'invalid');
  } catch {
    importUsernameValid = null;
    setUsernameFieldStatus(null);
  }
}

const debouncedValidateImportUsername = debounce(validateImportUsername, 500);

document.getElementById('source')?.addEventListener('change', (e) => {
  prefillUsername((e.target as HTMLSelectElement).value);
  saveFormValues();
  importUsernameValid = null;
  if ((document.getElementById('username') as HTMLInputElement | null)?.value.trim()) {
    debouncedValidateImportUsername();
  }
});
document.getElementById('username')?.addEventListener('input', () => {
  saveFormValues();
  importUsernameValid = null;
  const username = (document.getElementById('username') as HTMLInputElement | null)?.value.trim() ?? '';
  if (username) {
    setUsernameFieldStatus('checking');
    debouncedValidateImportUsername();
  } else {
    setUsernameFieldStatus(null);
  }
});
document.getElementById('maxGames')?.addEventListener('input', saveFormValues);

const importTracker = new ProgressTracker({
  progressContainerId: 'importProgress',
  fillId: 'importProgressFill',
  textId: 'importProgressText',
  startBtnId: 'source',
  messageId: 'importMessage',
  showMessage,
});

document.getElementById('importForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();

  const source = (document.getElementById('source') as HTMLSelectElement | null)?.value ?? '';
  const username = (document.getElementById('username') as HTMLInputElement | null)?.value.trim() ?? '';
  const maxGames = parseInt((document.getElementById('maxGames') as HTMLInputElement | null)?.value ?? '100');

  if (importUsernameValid === null && source && username) {
    setUsernameFieldStatus('checking');
    try {
      const result = await client.setup.validateUsername(source, username) as { valid: boolean };
      importUsernameValid = result.valid;
      setUsernameFieldStatus(result.valid ? 'valid' : 'invalid');
    } catch {
      importUsernameValid = null;
      setUsernameFieldStatus(null);
    }
  }

  if (importUsernameValid === false) {
    showMessage('importMessage', 'error', t('setup.username_invalid'));
    return;
  }

  try {
    const data = await client.jobs.startImport(source, username, maxGames) as { job_id: string };
    currentJobId = data.job_id;
    document.getElementById('importProgress')?.classList.remove('hidden');
    showMessage('importMessage', 'success', t('management.import.started'));
  } catch (err) {
    showMessage('importMessage', 'error', t('management.import.start_failed', { error: (err as Error).message }));
  }
});

async function startSync(): Promise<void> {
  const syncStatus = document.getElementById('syncStatus');
  if (!syncStatus) return;
  try {
    await client.jobs.startSync();
    syncStatus.innerHTML =
      '<div class="message success">' + t('management.sync.started') + '</div>';
  } catch (err) {
    syncStatus.innerHTML =
      '<div class="message error">' + t('management.sync.failed', { error: (err as Error).message }) + '</div>';
  }
}

initialize();

const analysisCard = new JobCard({
  progressContainerId: 'analysisProgress',
  fillId: 'analysisProgressFill',
  textId: 'analysisProgressText',
  startBtnId: 'startAnalysisBtn',
  stopBtnId: 'stopAnalysisBtn',
  messageId: 'analysisMessage',
  showMessage,
  pendingCountId: 'unanalyzedText',
  fetchPending: () => client.stats.overview() as Promise<Record<string, unknown>>,
  pendingField: 'pending_analysis',
  pendingMessageKey: 'management.analysis.pending',
  fetchStatus: () => client.analysis.status() as Promise<Record<string, unknown>>,
  startJob: () => client.analysis.start() as Promise<Record<string, unknown>>,
  stopJob: (jobId: string) => client.analysis.stop(jobId),
  startedMessage: t('management.analysis.started'),
  completedMessage: t('management.analysis.completed'),
  failedPrefix: t('management.analysis.failed', { error: '' }),
});

const backfillCard = new JobCard({
  progressContainerId: 'backfillProgress',
  fillId: 'backfillProgressFill',
  textId: 'backfillProgressText',
  startBtnId: 'startBackfillBtn',
  messageId: 'backfillMessage',
  showMessage,
  pendingCountId: 'backfillPendingText',
  pendingMessageKey: 'management.backfill_phases.pending',
  fetchPending: () => client.backfill.phasesPending() as Promise<Record<string, unknown>>,
  fetchStatus: () => client.backfill.phasesStatus() as Promise<Record<string, unknown>>,
  startJob: () => client.backfill.startPhases() as Promise<Record<string, unknown>>,
  startedMessage: t('management.backfill_phases.started'),
  completedMessage: t('management.backfill_phases.completed'),
  failedPrefix: t('management.backfill_phases.failed', { error: '' }),
});

const ecoBackfillCard = new JobCard({
  progressContainerId: 'ecoBackfillProgress',
  fillId: 'ecoBackfillProgressFill',
  textId: 'ecoBackfillProgressText',
  startBtnId: 'startEcoBackfillBtn',
  messageId: 'ecoBackfillMessage',
  showMessage,
  pendingCountId: 'ecoBackfillPendingText',
  pendingMessageKey: 'management.backfill_eco.pending',
  fetchPending: () => client.backfill.ecoPending() as Promise<Record<string, unknown>>,
  fetchStatus: () => client.backfill.ecoStatus() as Promise<Record<string, unknown>>,
  startJob: () => client.backfill.startEco() as Promise<Record<string, unknown>>,
  startedMessage: t('management.backfill_eco.started'),
  completedMessage: t('management.backfill_eco.completed'),
  failedPrefix: t('management.backfill_eco.failed', { error: '' }),
});

const trapsBackfillCard = new JobCard({
  progressContainerId: 'trapsBackfillProgress',
  fillId: 'trapsBackfillProgressFill',
  textId: 'trapsBackfillProgressText',
  startBtnId: 'startTrapsBackfillBtn',
  messageId: 'trapsBackfillMessage',
  showMessage,
  fetchStatus: () => client.backfill.trapsStatus() as Promise<Record<string, unknown>>,
  startJob: () => client.backfill.startTraps() as Promise<Record<string, unknown>>,
  startedMessage: t('management.backfill_traps.started'),
  completedMessage: t('management.backfill_traps.completed'),
  failedPrefix: t('management.backfill_traps.failed', { error: '' }),
});

const deleteAllCard = new JobCard({
  progressContainerId: 'deleteAllProgress',
  fillId: 'deleteAllProgressFill',
  textId: 'deleteAllProgressText',
  startBtnId: 'deleteAllBtn',
  messageId: 'deleteAllMessage',
  showMessage,
  textFormat: (current, total, percent) => `${current}/${total} tables (${percent}%)`,
  fetchStatus: () => client.data.deleteStatus() as Promise<Record<string, unknown>>,
  startJob: () => client.data.deleteAll() as Promise<Record<string, unknown>>,
  startedMessage: t('management.danger.started'),
  completedMessage: t('management.danger.completed'),
  failedPrefix: t('management.danger.failed', { error: '' }),
  onComplete: () => {
    clearAppLocalStorage();
    setTimeout(() => window.location.reload(), 2000);
  },
});

const jobCards = [analysisCard, backfillCard, ecoBackfillCard, deleteAllCard];

jobCards.forEach(card => card.loadStatus());

async function confirmDeleteAll(): Promise<void> {
  if (!confirm(t('management.danger.confirm1'))) return;
  if (!confirm(t('management.danger.confirm2'))) return;

  await deleteAllCard.start();
}

wsClient.connect();

wsClient.subscribe([
  'job.created',
  'job.status_changed',
  'job.progress_updated',
  'job.completed',
  'job.failed',
]);

const debouncedRefreshJobsTable = debounce(refreshJobsTable, 1000);

wsClient.on('job.progress_updated', (data) => {
  const progress = data as JobProgressData;
  if (progress.job_id === currentJobId) {
    importTracker.updateProgress(progress.current, progress.total, progress.percent);
  }

  for (const card of jobCards) {
    if (card.handleProgress(progress)) break;
  }

  debouncedRefreshJobsTable();
});

wsClient.on('job.status_changed', (data) => {
  const status = data as JobStatusData;
  if (status.job_id === currentJobId) {
    if (status.status === 'completed') {
      document.getElementById('importProgress')?.classList.add('hidden');
      showMessage('importMessage', 'success', t('management.import.completed'));
      currentJobId = null;
    } else if (status.status === 'failed') {
      document.getElementById('importProgress')?.classList.add('hidden');
      showMessage('importMessage', 'error', t('management.import.failed', { error: status.error_message || 'Unknown error' }));
      currentJobId = null;
    }
  }

  for (const card of jobCards) {
    if (card.handleStatusChange(status)) break;
  }

  refreshJobsTable();
});

wsClient.on('job.created', () => {
  refreshJobsTable();
});

document.getElementById('syncBtn')?.addEventListener('click', startSync);
document.getElementById('startAnalysisBtn')?.addEventListener('click', () => analysisCard.start());
document.getElementById('stopAnalysisBtn')?.addEventListener('click', () => analysisCard.stop(refreshJobsTable));
document.getElementById('startBackfillBtn')?.addEventListener('click', () => backfillCard.start());
document.getElementById('startEcoBackfillBtn')?.addEventListener('click', () => ecoBackfillCard.start());
const trapsBackfillBtn = document.getElementById('startTrapsBackfillBtn');
if (trapsBackfillBtn) trapsBackfillBtn.addEventListener('click', () => trapsBackfillCard.start());
document.getElementById('deleteAllBtn')?.addEventListener('click', confirmDeleteAll);
