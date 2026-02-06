import { WebSocketClient } from './websocket-client.js';
import { ProgressTracker } from './progress-tracker.js';
import { JobCard } from './job-card.js';
import { loadConfiguredUsernames } from './usernames.js';
import { client } from './api.js';

const wsClient = new WebSocketClient();

let currentJobId = null;
let configuredUsernames = {};

const STORAGE_KEYS = {
  source: 'blunder_import_source',
  username: 'blunder_import_username',
  maxGames: 'blunder_import_maxGames'
};

// Engine status (unique, not a job card)
async function loadEngineStatus() {
  const container = document.getElementById('engineStatus');
  try {
    const data = await client.system.engineStatus();

    if (data.available) {
      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--success);"></span>
          <span style="font-weight: 600; color: var(--success);">Engine Available</span>
        </div>
        <table style="font-size: 0.875rem; color: var(--text-muted);">
          <tr><td style="padding-right: 16px;">Name:</td><td style="font-family: monospace;">${data.name || 'Unknown'}</td></tr>
          <tr><td style="padding-right: 16px;">Path:</td><td style="font-family: monospace;">${data.path || 'Unknown'}</td></tr>
        </table>
      `;
    } else {
      container.innerHTML = `
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--error);"></span>
          <span style="font-weight: 600; color: var(--error);">Engine Unavailable</span>
        </div>
        <p style="color: var(--text-muted); font-size: 0.875rem;">
          Path: <code>${data.path || 'Not configured'}</code><br>
          Please ensure Stockfish is installed and the path is correct.
        </p>
      `;
    }
  } catch (err) {
    container.innerHTML = `
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--error);"></span>
        <span style="color: var(--error);">Failed to load engine status: ${err.message}</span>
      </div>
    `;
    console.error('Failed to load engine status:', err);
  }
}

loadEngineStatus();

function refreshJobsTable() {
  htmx.trigger(document.body, 'jobsRefresh');
}

function showMessage(elementId, type, text) {
  const el = document.getElementById(elementId);
  el.className = 'message ' + type;
  el.textContent = text;
  el.style.display = 'block';
  setTimeout(() => { el.style.display = 'none'; }, 5000);
}

// --- Import (form-driven, not a JobCard) ---

function prefillUsername(source) {
  const usernameInput = document.getElementById('username');
  const currentValue = usernameInput.value.trim();

  if (!currentValue && source) {
    if (source === 'lichess' && configuredUsernames.lichess_username) {
      usernameInput.value = configuredUsernames.lichess_username;
    } else if (source === 'chesscom' && configuredUsernames.chesscom_username) {
      usernameInput.value = configuredUsernames.chesscom_username;
    }
  }
}

function saveFormValues() {
  localStorage.setItem(STORAGE_KEYS.source, document.getElementById('source').value);
  localStorage.setItem(STORAGE_KEYS.username, document.getElementById('username').value);
  localStorage.setItem(STORAGE_KEYS.maxGames, document.getElementById('maxGames').value);
}

function restoreFormValues() {
  const savedSource = localStorage.getItem(STORAGE_KEYS.source);
  const savedUsername = localStorage.getItem(STORAGE_KEYS.username);
  const savedMaxGames = localStorage.getItem(STORAGE_KEYS.maxGames);

  if (savedSource) document.getElementById('source').value = savedSource;
  if (savedUsername) document.getElementById('username').value = savedUsername;
  if (savedMaxGames) document.getElementById('maxGames').value = savedMaxGames;
}

async function initialize() {
  configuredUsernames = await loadConfiguredUsernames();
  restoreFormValues();

  const restoredSource = document.getElementById('source').value;
  if (restoredSource && !document.getElementById('username').value) {
    prefillUsername(restoredSource);
  }
}

document.getElementById('source').addEventListener('change', (e) => {
  prefillUsername(e.target.value);
  saveFormValues();
});
document.getElementById('username').addEventListener('input', saveFormValues);
document.getElementById('maxGames').addEventListener('input', saveFormValues);

const importTracker = new ProgressTracker({
  progressContainerId: 'importProgress',
  fillId: 'importProgressFill',
  textId: 'importProgressText',
  startBtnId: 'source',
  messageId: 'importMessage',
  showMessage
});

document.getElementById('importForm').addEventListener('submit', async (e) => {
  e.preventDefault();

  const source = document.getElementById('source').value;
  const username = document.getElementById('username').value;
  const maxGames = parseInt(document.getElementById('maxGames').value);

  try {
    const data = await client.jobs.startImport(source, username, maxGames);
    currentJobId = data.job_id;
    document.getElementById('importProgress').style.display = 'block';
    showMessage('importMessage', 'success', 'Import job started!');
  } catch (err) {
    showMessage('importMessage', 'error', 'Failed to start import: ' + err.message);
  }
});

// --- Sync (one-shot, not a JobCard) ---

async function startSync() {
  try {
    await client.jobs.startSync();
    document.getElementById('syncStatus').innerHTML =
      '<div class="message success">Sync started! Check Recent Jobs for progress.</div>';
  } catch (err) {
    document.getElementById('syncStatus').innerHTML =
      '<div class="message error">Failed to start sync: ' + err.message + '</div>';
  }
}

initialize();

// --- Job Cards ---

const analysisCard = new JobCard({
  progressContainerId: 'analysisProgress',
  fillId: 'analysisProgressFill',
  textId: 'analysisProgressText',
  startBtnId: 'startAnalysisBtn',
  stopBtnId: 'stopAnalysisBtn',
  messageId: 'analysisMessage',
  showMessage,
  pendingCountId: 'unanalyzedCount',
  fetchPending: () => client.stats.overview(),
  pendingField: 'pending_analysis',
  fetchStatus: () => client.analysis.status(),
  startJob: () => client.analysis.start(),
  stopJob: (jobId) => client.analysis.stop(jobId),
  startedMessage: 'Analysis started!',
  completedMessage: 'Analysis completed!',
  failedPrefix: 'Analysis failed: ',
});

const backfillCard = new JobCard({
  progressContainerId: 'backfillProgress',
  fillId: 'backfillProgressFill',
  textId: 'backfillProgressText',
  startBtnId: 'startBackfillBtn',
  messageId: 'backfillMessage',
  showMessage,
  pendingCountId: 'backfillPendingCount',
  fetchPending: () => client.backfill.phasesPending(),
  fetchStatus: () => client.backfill.phasesStatus(),
  startJob: () => client.backfill.startPhases(),
  startedMessage: 'Backfill started!',
  completedMessage: 'Backfill completed!',
  failedPrefix: 'Backfill failed: ',
});

const ecoBackfillCard = new JobCard({
  progressContainerId: 'ecoBackfillProgress',
  fillId: 'ecoBackfillProgressFill',
  textId: 'ecoBackfillProgressText',
  startBtnId: 'startEcoBackfillBtn',
  messageId: 'ecoBackfillMessage',
  showMessage,
  pendingCountId: 'ecoBackfillPendingCount',
  fetchPending: () => client.backfill.ecoPending(),
  fetchStatus: () => client.backfill.ecoStatus(),
  startJob: () => client.backfill.startEco(),
  startedMessage: 'ECO backfill started!',
  completedMessage: 'ECO backfill completed!',
  failedPrefix: 'ECO backfill failed: ',
});

const deleteAllCard = new JobCard({
  progressContainerId: 'deleteAllProgress',
  fillId: 'deleteAllProgressFill',
  textId: 'deleteAllProgressText',
  startBtnId: 'deleteAllBtn',
  messageId: 'deleteAllMessage',
  showMessage,
  textFormat: (current, total, percent) => `${current}/${total} tables (${percent}%)`,
  fetchStatus: () => client.data.deleteStatus(),
  startJob: () => client.data.deleteAll(),
  startedMessage: 'Delete job started!',
  completedMessage: 'All data deleted! Refreshing page...',
  failedPrefix: 'Delete failed: ',
  onComplete: () => setTimeout(() => window.location.reload(), 2000),
});

const jobCards = [analysisCard, backfillCard, ecoBackfillCard, deleteAllCard];

// Load all statuses on page load
jobCards.forEach(card => card.loadStatus());

// Delete requires double confirmation before starting
async function confirmDeleteAll() {
  if (!confirm(
    'Are you sure you want to delete ALL data?\n\n' +
    'This will permanently remove:\n' +
    '• All imported games\n' +
    '• All analysis results\n' +
    '• All puzzle attempts\n' +
    '• All job history\n\n' +
    'This action cannot be undone!'
  )) return;

  if (!confirm(
    'This is your final warning!\n\n' +
    'Click OK to permanently delete all data.'
  )) return;

  await deleteAllCard.start();
}

// --- WebSocket ---

wsClient.connect();

wsClient.subscribe([
  'job.created',
  'job.status_changed',
  'job.progress_updated',
  'job.completed',
  'job.failed'
]);

let jobsRefreshTimeout = null;
function debouncedRefreshJobsTable() {
  if (jobsRefreshTimeout) return;
  jobsRefreshTimeout = setTimeout(() => {
    refreshJobsTable();
    jobsRefreshTimeout = null;
  }, 1000);
}

wsClient.on('job.progress_updated', (data) => {
  // Import tracker (not a JobCard)
  if (data.job_id === currentJobId) {
    importTracker.updateProgress(data.current, data.total, data.percent);
  }

  // Job cards
  for (const card of jobCards) {
    if (card.handleProgress(data)) break;
  }

  debouncedRefreshJobsTable();
});

wsClient.on('job.status_changed', (data) => {
  // Import (not a JobCard)
  if (data.job_id === currentJobId) {
    if (data.status === 'completed') {
      document.getElementById('importProgress').style.display = 'none';
      showMessage('importMessage', 'success', 'Import completed!');
      currentJobId = null;
    } else if (data.status === 'failed') {
      document.getElementById('importProgress').style.display = 'none';
      showMessage('importMessage', 'error', 'Import failed: ' + (data.error_message || 'Unknown error'));
      currentJobId = null;
    }
  }

  // Job cards
  for (const card of jobCards) {
    if (card.handleStatusChange(data)) break;
  }

  refreshJobsTable();
});

wsClient.on('job.created', () => {
  refreshJobsTable();
});

// --- Button wiring ---

document.getElementById('syncBtn').addEventListener('click', startSync);
document.getElementById('startAnalysisBtn').addEventListener('click', () => analysisCard.start());
document.getElementById('stopAnalysisBtn').addEventListener('click', () => analysisCard.stop(refreshJobsTable));
document.getElementById('startBackfillBtn').addEventListener('click', () => backfillCard.start());
document.getElementById('startEcoBackfillBtn').addEventListener('click', () => ecoBackfillCard.start());
document.getElementById('deleteAllBtn').addEventListener('click', confirmDeleteAll);
