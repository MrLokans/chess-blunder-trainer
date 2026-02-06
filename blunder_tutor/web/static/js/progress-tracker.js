window.ProgressTracker = class ProgressTracker {
  constructor({
    progressContainerId,
    fillId,
    textId,
    startBtnId,
    stopBtnId = null,
    messageId,
    textFormat = null
  }) {
    this.progressContainer = document.getElementById(progressContainerId);
    this.fill = document.getElementById(fillId);
    this.text = document.getElementById(textId);
    this.startBtn = document.getElementById(startBtnId);
    this.stopBtn = stopBtnId ? document.getElementById(stopBtnId) : null;
    this.messageId = messageId;
    this.textFormat = textFormat || ((current, total, percent) => `${current}/${total} (${percent}%)`);
  }

  show(job) {
    this.progressContainer.style.display = 'block';
    this.startBtn.style.display = 'none';
    if (this.stopBtn) this.stopBtn.style.display = 'inline-block';

    if (job && job.progress_total > 0) {
      this.updateProgress(job.progress_current, job.progress_total,
        Math.round((job.progress_current / job.progress_total) * 100));
    }
  }

  hide() {
    this.progressContainer.style.display = 'none';
    this.startBtn.style.display = 'inline-block';
    if (this.stopBtn) this.stopBtn.style.display = 'none';
  }

  updateProgress(current, total, percent) {
    this.fill.style.width = percent + '%';
    this.text.textContent = this.textFormat(current, total, percent);
  }

  showMessage(type, text) {
    window.showMessage(this.messageId, type, text);
  }
};
