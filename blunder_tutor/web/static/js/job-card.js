import { ProgressTracker } from './progress-tracker.js';

export class JobCard {
  constructor({
    progressContainerId,
    fillId,
    textId,
    startBtnId,
    stopBtnId = null,
    messageId,
    showMessage,
    textFormat = null,
    pendingCountId = null,
    fetchPending = null,
    pendingField = 'pending_count',
    fetchStatus,
    startJob,
    stopJob = null,
    startedMessage = 'Job started!',
    completedMessage = 'Job completed!',
    failedPrefix = 'Job failed: ',
    onComplete = null,
  }) {
    this.jobId = null;
    this._showMessage = showMessage;
    this.messageId = messageId;
    this.pendingCountId = pendingCountId;
    this.fetchPending = fetchPending;
    this.pendingField = pendingField;
    this.fetchStatus = fetchStatus;
    this.startJob = startJob;
    this.stopJob = stopJob;
    this.startedMessage = startedMessage;
    this.completedMessage = completedMessage;
    this.failedPrefix = failedPrefix;
    this.onComplete = onComplete;

    this.tracker = new ProgressTracker({
      progressContainerId,
      fillId,
      textId,
      startBtnId,
      stopBtnId,
      messageId,
      showMessage,
      textFormat
    });
  }

  async loadStatus() {
    try {
      if (this.fetchPending && this.pendingCountId) {
        const pending = await this.fetchPending();
        document.getElementById(this.pendingCountId).textContent =
          pending[this.pendingField] || 0;
      }

      const status = await this.fetchStatus();

      if (status.status === 'running') {
        this.jobId = status.job_id;
        this.tracker.show(status);
      } else {
        this.tracker.hide();
      }
    } catch (err) {
      console.error(`Failed to load status for ${this.messageId}:`, err);
    }
  }

  async start() {
    try {
      const data = await this.startJob();
      this.jobId = data.job_id;
      this._showMessage(this.messageId, 'success', this.startedMessage);
      this.tracker.show(null);
    } catch (err) {
      this._showMessage(this.messageId, 'error', this.failedPrefix + err.message);
    }
  }

  async stop(refreshCallback) {
    if (!this.jobId || !this.stopJob) return;

    try {
      await this.stopJob(this.jobId);
      this._showMessage(this.messageId, 'success', 'Stopped!');
      this.tracker.hide();
      this.jobId = null;
      if (refreshCallback) refreshCallback();
      this.loadStatus();
    } catch (err) {
      this._showMessage(this.messageId, 'error', 'Failed to stop: ' + err.message);
    }
  }

  handleStatusChange(data) {
    if (data.job_id !== this.jobId) return false;

    if (data.status === 'completed') {
      this.tracker.hide();
      this.jobId = null;
      this._showMessage(this.messageId, 'success', this.completedMessage);
      if (this.onComplete) {
        this.onComplete();
      } else {
        this.loadStatus();
      }
    } else if (data.status === 'failed') {
      this.tracker.hide();
      this.jobId = null;
      this._showMessage(this.messageId, 'error',
        this.failedPrefix + (data.error_message || 'Unknown error'));
      this.loadStatus();
    }

    return true;
  }

  handleProgress(data) {
    if (data.job_id !== this.jobId) return false;
    this.tracker.updateProgress(data.current, data.total, data.percent);
    return true;
  }
}
