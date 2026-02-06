import { WebSocketClient } from './websocket-client.js';
import { ProgressTracker } from './progress-tracker.js';
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

function showMessage(elementId, type, text) {
  const el = document.getElementById(elementId);
  el.className = 'message ' + type;
  el.textContent = text;
  el.style.display = 'block';

  setTimeout(() => {
    el.style.display = 'none';
  }, 5000);
}

// Import progress tracker
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

// Analysis
let analysisJobId = null;

const analysisTracker = new ProgressTracker({
  progressContainerId: 'analysisProgress',
  fillId: 'analysisProgressFill',
  textId: 'analysisProgressText',
  startBtnId: 'startAnalysisBtn',
  stopBtnId: 'stopAnalysisBtn',
  messageId: 'analysisMessage',
  showMessage
});

async function loadAnalysisStatus() {
  try {
    const stats = await client.stats.overview();
    document.getElementById('unanalyzedCount').textContent = stats.pending_analysis || 0;

    const status = await client.analysis.status();

    if (status.status === 'running') {
      analysisJobId = status.job_id;
      analysisTracker.show(status);
    } else {
      analysisTracker.hide();
    }
  } catch (err) {
    console.error('Failed to load analysis status:', err);
  }
}

async function startAnalysis() {
  try {
    const data = await client.analysis.start();
    analysisJobId = data.job_id;
    showMessage('analysisMessage', 'success', 'Analysis started!');
    analysisTracker.show(null);
  } catch (err) {
    showMessage('analysisMessage', 'error', 'Failed to start analysis: ' + err.message);
  }
}

async function stopAnalysis() {
  if (!analysisJobId) return;

  try {
    await client.analysis.stop(analysisJobId);
    showMessage('analysisMessage', 'success', 'Analysis stopped!');
    analysisTracker.hide();
    analysisJobId = null;
    refreshJobsTable();
    loadAnalysisStatus();
  } catch (err) {
    showMessage('analysisMessage', 'error', 'Failed to stop analysis: ' + err.message);
  }
}

loadAnalysisStatus();

// Backfill phases
let backfillJobId = null;

const backfillTracker = new ProgressTracker({
  progressContainerId: 'backfillProgress',
  fillId: 'backfillProgressFill',
  textId: 'backfillProgressText',
  startBtnId: 'startBackfillBtn',
  messageId: 'backfillMessage',
  showMessage
});

async function loadBackfillStatus() {
  try {
    const pending = await client.backfill.phasesPending();
    document.getElementById('backfillPendingCount').textContent = pending.pending_count || 0;

    const status = await client.backfill.phasesStatus();

    if (status.status === 'running') {
      backfillJobId = status.job_id;
      backfillTracker.show(status);
    } else {
      backfillTracker.hide();
    }
  } catch (err) {
    console.error('Failed to load backfill status:', err);
  }
}

async function startBackfillPhases() {
  try {
    const data = await client.backfill.startPhases();
    backfillJobId = data.job_id;
    showMessage('backfillMessage', 'success', 'Backfill started!');
    backfillTracker.show(null);
  } catch (err) {
    showMessage('backfillMessage', 'error', 'Failed to start backfill: ' + err.message);
  }
}

loadBackfillStatus();

// ECO backfill
let ecoBackfillJobId = null;

const ecoBackfillTracker = new ProgressTracker({
  progressContainerId: 'ecoBackfillProgress',
  fillId: 'ecoBackfillProgressFill',
  textId: 'ecoBackfillProgressText',
  startBtnId: 'startEcoBackfillBtn',
  messageId: 'ecoBackfillMessage',
  showMessage
});

async function loadECOBackfillStatus() {
  try {
    const pending = await client.backfill.ecoPending();
    document.getElementById('ecoBackfillPendingCount').textContent = pending.pending_count || 0;

    const status = await client.backfill.ecoStatus();

    if (status.status === 'running') {
      ecoBackfillJobId = status.job_id;
      ecoBackfillTracker.show(status);
    } else {
      ecoBackfillTracker.hide();
    }
  } catch (err) {
    console.error('Failed to load ECO backfill status:', err);
  }
}

async function startBackfillECO() {
  try {
    const data = await client.backfill.startEco();
    ecoBackfillJobId = data.job_id;
    showMessage('ecoBackfillMessage', 'success', 'ECO backfill started!');
    ecoBackfillTracker.show(null);
  } catch (err) {
    showMessage('ecoBackfillMessage', 'error', 'Failed to start ECO backfill: ' + err.message);
  }
}

loadECOBackfillStatus();

// Delete all data
let deleteAllJobId = null;

const deleteAllTracker = new ProgressTracker({
  progressContainerId: 'deleteAllProgress',
  fillId: 'deleteAllProgressFill',
  textId: 'deleteAllProgressText',
  startBtnId: 'deleteAllBtn',
  messageId: 'deleteAllMessage',
  showMessage,
  textFormat: (current, total, percent) => `${current}/${total} tables (${percent}%)`
});

async function loadDeleteAllStatus() {
  try {
    const status = await client.data.deleteStatus();

    if (status.status === 'running') {
      deleteAllJobId = status.job_id;
      deleteAllTracker.show(status);
    } else {
      deleteAllTracker.hide();
    }
  } catch (err) {
    console.error('Failed to load delete all status:', err);
  }
}

async function confirmDeleteAll() {
  const confirmed = confirm(
    'Are you sure you want to delete ALL data?\n\n' +
    'This will permanently remove:\n' +
    '• All imported games\n' +
    '• All analysis results\n' +
    '• All puzzle attempts\n' +
    '• All job history\n\n' +
    'This action cannot be undone!'
  );

  if (!confirmed) return;

  const doubleConfirmed = confirm(
    'This is your final warning!\n\n' +
    'Click OK to permanently delete all data.'
  );

  if (!doubleConfirmed) return;

  try {
    const data = await client.data.deleteAll();
    if (data.job_id) {
      deleteAllJobId = data.job_id;
      showMessage('deleteAllMessage', 'success', 'Delete job started!');
      deleteAllTracker.show(null);
    } else {
      showMessage('deleteAllMessage', 'error', 'Failed to start delete job');
    }
  } catch (err) {
    showMessage('deleteAllMessage', 'error', 'Failed to delete data: ' + err.message);
  }
}

loadDeleteAllStatus();

// WebSocket
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

function getTrackerForJob(jobId) {
  if (jobId === currentJobId) return importTracker;
  if (jobId === analysisJobId) return analysisTracker;
  if (jobId === backfillJobId) return backfillTracker;
  if (jobId === ecoBackfillJobId) return ecoBackfillTracker;
  if (jobId === deleteAllJobId) return deleteAllTracker;
  return null;
}

wsClient.on('job.progress_updated', (data) => {
  const tracker = getTrackerForJob(data.job_id);
  if (tracker) {
    tracker.updateProgress(data.current, data.total, data.percent);
  }
  debouncedRefreshJobsTable();
});

wsClient.on('job.status_changed', (data) => {
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

  if (data.job_id === analysisJobId) {
    if (data.status === 'completed') {
      analysisTracker.hide();
      analysisJobId = null;
      showMessage('analysisMessage', 'success', 'Analysis completed!');
      loadAnalysisStatus();
    } else if (data.status === 'failed') {
      analysisTracker.hide();
      analysisJobId = null;
      showMessage('analysisMessage', 'error', 'Analysis failed: ' + (data.error_message || 'Unknown error'));
      loadAnalysisStatus();
    }
  }

  if (data.job_id === backfillJobId) {
    if (data.status === 'completed') {
      backfillTracker.hide();
      backfillJobId = null;
      showMessage('backfillMessage', 'success', 'Backfill completed!');
      loadBackfillStatus();
    } else if (data.status === 'failed') {
      backfillTracker.hide();
      backfillJobId = null;
      showMessage('backfillMessage', 'error', 'Backfill failed: ' + (data.error_message || 'Unknown error'));
      loadBackfillStatus();
    }
  }

  if (data.job_id === ecoBackfillJobId) {
    if (data.status === 'completed') {
      ecoBackfillTracker.hide();
      ecoBackfillJobId = null;
      showMessage('ecoBackfillMessage', 'success', 'ECO backfill completed!');
      loadECOBackfillStatus();
    } else if (data.status === 'failed') {
      ecoBackfillTracker.hide();
      ecoBackfillJobId = null;
      showMessage('ecoBackfillMessage', 'error', 'ECO backfill failed: ' + (data.error_message || 'Unknown error'));
      loadECOBackfillStatus();
    }
  }

  if (data.job_id === deleteAllJobId) {
    if (data.status === 'completed') {
      deleteAllTracker.hide();
      deleteAllJobId = null;
      showMessage('deleteAllMessage', 'success', 'All data deleted! Refreshing page...');
      setTimeout(() => window.location.reload(), 2000);
    } else if (data.status === 'failed') {
      deleteAllTracker.hide();
      deleteAllJobId = null;
      showMessage('deleteAllMessage', 'error', 'Delete failed: ' + (data.error_message || 'Unknown error'));
    }
  }

  refreshJobsTable();
});

wsClient.on('job.created', () => {
  refreshJobsTable();
});

// Wire up button event listeners
document.getElementById('syncBtn').addEventListener('click', startSync);
document.getElementById('startAnalysisBtn').addEventListener('click', startAnalysis);
document.getElementById('stopAnalysisBtn').addEventListener('click', stopAnalysis);
document.getElementById('startBackfillBtn').addEventListener('click', startBackfillPhases);
document.getElementById('startEcoBackfillBtn').addEventListener('click', startBackfillECO);
document.getElementById('deleteAllBtn').addEventListener('click', confirmDeleteAll);
