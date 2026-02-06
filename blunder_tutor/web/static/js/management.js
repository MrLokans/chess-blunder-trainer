  let currentJobId = null;
  let configuredUsernames = {};

  // LocalStorage keys
  const STORAGE_KEYS = {
    source: 'blunder_import_source',
    username: 'blunder_import_username',
    maxGames: 'blunder_import_maxGames'
  };

  // Load engine status
  async function loadEngineStatus() {
    const container = document.getElementById('engineStatus');
    try {
      const resp = await fetch('/api/system/engine');
      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      }
      const data = await resp.json();

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

  // Load engine status on page load
  loadEngineStatus();

  // Trigger HTMX refresh of jobs table
  function refreshJobsTable() {
    htmx.trigger(document.body, 'jobsRefresh');
  }

  // Prefill username based on selected source
  function prefillUsername(source) {
    const usernameInput = document.getElementById('username');
    const currentValue = usernameInput.value.trim();

    // Only prefill if field is empty
    if (!currentValue && source) {
      if (source === 'lichess' && configuredUsernames.lichess_username) {
        usernameInput.value = configuredUsernames.lichess_username;
      } else if (source === 'chesscom' && configuredUsernames.chesscom_username) {
        usernameInput.value = configuredUsernames.chesscom_username;
      }
    }
  }

  // Save form values to localStorage
  function saveFormValues() {
    localStorage.setItem(STORAGE_KEYS.source, document.getElementById('source').value);
    localStorage.setItem(STORAGE_KEYS.username, document.getElementById('username').value);
    localStorage.setItem(STORAGE_KEYS.maxGames, document.getElementById('maxGames').value);
  }

  // Restore form values from localStorage
  function restoreFormValues() {
    const savedSource = localStorage.getItem(STORAGE_KEYS.source);
    const savedUsername = localStorage.getItem(STORAGE_KEYS.username);
    const savedMaxGames = localStorage.getItem(STORAGE_KEYS.maxGames);

    if (savedSource) {
      document.getElementById('source').value = savedSource;
    }
    if (savedUsername) {
      document.getElementById('username').value = savedUsername;
    }
    if (savedMaxGames) {
      document.getElementById('maxGames').value = savedMaxGames;
    }
  }

  // Initialize: Load configured usernames and restore form values
  async function initialize() {
    configuredUsernames = await loadConfiguredUsernames();
    restoreFormValues();

    // Prefill username based on restored source
    const restoredSource = document.getElementById('source').value;
    if (restoredSource && !document.getElementById('username').value) {
      prefillUsername(restoredSource);
    }
  }

  // Add event listener for source change
  document.getElementById('source').addEventListener('change', (e) => {
    prefillUsername(e.target.value);
    saveFormValues();
  });

  // Add event listeners to save form values on change
  document.getElementById('username').addEventListener('input', saveFormValues);
  document.getElementById('maxGames').addEventListener('input', saveFormValues);

  // Import progress tracker (no stop button, default text format)
  const importTracker = new ProgressTracker({
    progressContainerId: 'importProgress',
    fillId: 'importProgressFill',
    textId: 'importProgressText',
    startBtnId: 'source',
    messageId: 'importMessage'
  });

  document.getElementById('importForm').addEventListener('submit', async (e) => {
    e.preventDefault();

    const source = document.getElementById('source').value;
    const username = document.getElementById('username').value;
    const maxGames = parseInt(document.getElementById('maxGames').value);

    try {
      const resp = await fetch('/api/import/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source, username, max_games: maxGames })
      });

      const data = await resp.json();

      if (data.error) {
        showMessage('importMessage', 'error', 'Error: ' + data.error);
        return;
      }

      currentJobId = data.job_id;
      document.getElementById('importProgress').style.display = 'block';
      showMessage('importMessage', 'success', 'Import job started!');

    } catch (err) {
      showMessage('importMessage', 'error', 'Failed to start import: ' + err.message);
    }
  });

  async function startSync() {
    try {
      const resp = await fetch('/api/sync/start', { method: 'POST' });
      const data = await resp.json();

      document.getElementById('syncStatus').innerHTML =
        '<div class="message success">Sync started! Check Recent Jobs for progress.</div>';

    } catch (err) {
      document.getElementById('syncStatus').innerHTML =
        '<div class="message error">Failed to start sync: ' + err.message + '</div>';
    }
  }

  function showMessage(elementId, type, text) {
    const el = document.getElementById(elementId);
    el.className = 'message ' + type;
    el.textContent = text;
    el.style.display = 'block';

    setTimeout(() => {
      el.style.display = 'none';
    }, 5000);
  }

  // Make showMessage globally accessible for ProgressTracker
  window.showMessage = showMessage;

  // Initialize on page load
  initialize();

  // Analysis progress tracker
  let analysisJobId = null;

  const analysisTracker = new ProgressTracker({
    progressContainerId: 'analysisProgress',
    fillId: 'analysisProgressFill',
    textId: 'analysisProgressText',
    startBtnId: 'startAnalysisBtn',
    stopBtnId: 'stopAnalysisBtn',
    messageId: 'analysisMessage'
  });

  async function loadAnalysisStatus() {
    try {
      const statsResp = await fetch('/api/stats');
      const stats = await statsResp.json();
      document.getElementById('unanalyzedCount').textContent = stats.pending_analysis || 0;

      const statusResp = await fetch('/api/analysis/status');
      const status = await statusResp.json();

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
      const resp = await fetch('/api/analysis/start', { method: 'POST' });
      const data = await resp.json();

      if (data.error) {
        showMessage('analysisMessage', 'error', 'Error: ' + data.error);
        return;
      }

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
      const resp = await fetch(`/api/analysis/stop/${analysisJobId}`, { method: 'POST' });
      const data = await resp.json();

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

  // Backfill phases progress tracker
  let backfillJobId = null;

  const backfillTracker = new ProgressTracker({
    progressContainerId: 'backfillProgress',
    fillId: 'backfillProgressFill',
    textId: 'backfillProgressText',
    startBtnId: 'startBackfillBtn',
    messageId: 'backfillMessage'
  });

  async function loadBackfillStatus() {
    try {
      const pendingResp = await fetch('/api/backfill-phases/pending');
      const pending = await pendingResp.json();
      document.getElementById('backfillPendingCount').textContent = pending.pending_count || 0;

      const statusResp = await fetch('/api/backfill-phases/status');
      const status = await statusResp.json();

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
      const resp = await fetch('/api/backfill-phases/start', { method: 'POST' });
      const data = await resp.json();

      if (data.detail) {
        showMessage('backfillMessage', 'error', 'Error: ' + data.detail);
        return;
      }

      backfillJobId = data.job_id;
      showMessage('backfillMessage', 'success', 'Backfill started!');
      backfillTracker.show(null);
    } catch (err) {
      showMessage('backfillMessage', 'error', 'Failed to start backfill: ' + err.message);
    }
  }

  loadBackfillStatus();

  // ECO backfill progress tracker
  let ecoBackfillJobId = null;

  const ecoBackfillTracker = new ProgressTracker({
    progressContainerId: 'ecoBackfillProgress',
    fillId: 'ecoBackfillProgressFill',
    textId: 'ecoBackfillProgressText',
    startBtnId: 'startEcoBackfillBtn',
    messageId: 'ecoBackfillMessage'
  });

  async function loadECOBackfillStatus() {
    try {
      const pendingResp = await fetch('/api/backfill-eco/pending');
      const pending = await pendingResp.json();
      document.getElementById('ecoBackfillPendingCount').textContent = pending.pending_count || 0;

      const statusResp = await fetch('/api/backfill-eco/status');
      const status = await statusResp.json();

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
      const resp = await fetch('/api/backfill-eco/start', { method: 'POST' });
      const data = await resp.json();

      if (data.detail) {
        showMessage('ecoBackfillMessage', 'error', 'Error: ' + data.detail);
        return;
      }

      ecoBackfillJobId = data.job_id;
      showMessage('ecoBackfillMessage', 'success', 'ECO backfill started!');
      ecoBackfillTracker.show(null);
    } catch (err) {
      showMessage('ecoBackfillMessage', 'error', 'Failed to start ECO backfill: ' + err.message);
    }
  }

  loadECOBackfillStatus();

  // Delete all data progress tracker
  let deleteAllJobId = null;

  const deleteAllTracker = new ProgressTracker({
    progressContainerId: 'deleteAllProgress',
    fillId: 'deleteAllProgressFill',
    textId: 'deleteAllProgressText',
    startBtnId: 'deleteAllBtn',
    messageId: 'deleteAllMessage',
    textFormat: (current, total, percent) => `${current}/${total} tables (${percent}%)`
  });

  async function loadDeleteAllStatus() {
    try {
      const statusResp = await fetch('/api/data/delete-status');
      const status = await statusResp.json();

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
      const resp = await fetch('/api/data/all', { method: 'DELETE' });
      const data = await resp.json();

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

  // Initialize WebSocket for real-time updates
  wsClient.connect();

  wsClient.subscribe([
    'job.created',
    'job.status_changed',
    'job.progress_updated',
    'job.completed',
    'job.failed'
  ]);

  // Debounced HTMX refresh (at most once per second)
  let jobsRefreshTimeout = null;
  function debouncedRefreshJobsTable() {
    if (jobsRefreshTimeout) return;
    jobsRefreshTimeout = setTimeout(() => {
      refreshJobsTable();
      jobsRefreshTimeout = null;
    }, 1000);
  }

  // Job ID to tracker mapping for progress updates
  function getTrackerForJob(jobId) {
    if (jobId === currentJobId) return { tracker: importTracker, fillId: 'importProgressFill', textId: 'importProgressText' };
    if (jobId === analysisJobId) return { tracker: analysisTracker };
    if (jobId === backfillJobId) return { tracker: backfillTracker };
    if (jobId === ecoBackfillJobId) return { tracker: ecoBackfillTracker };
    if (jobId === deleteAllJobId) return { tracker: deleteAllTracker };
    return null;
  }

  wsClient.on('job.progress_updated', (data) => {
    const match = getTrackerForJob(data.job_id);
    if (match) {
      match.tracker.updateProgress(data.current, data.total, data.percent);
    }
    debouncedRefreshJobsTable();
  });

  wsClient.on('job.status_changed', (data) => {
    // Handle import job completion
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

    // Handle analysis job completion
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

    // Handle backfill job completion
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

    // Handle ECO backfill job completion
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

    // Handle delete all job completion
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
