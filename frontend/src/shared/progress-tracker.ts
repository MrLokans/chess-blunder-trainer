export interface ProgressTrackerOptions {
  progressContainerId: string;
  fillId: string;
  textId: string;
  startBtnId: string;
  stopBtnId?: string | null;
  messageId: string;
  showMessage: (elementId: string, type: string, text: string) => void;
  textFormat?: ((current: number, total: number, percent: number) => string) | null;
}

export interface ProgressJob {
  progress_current: number;
  progress_total: number;
}

export class ProgressTracker {
  progressContainer: HTMLElement | null;
  fill: HTMLElement | null;
  text: HTMLElement | null;
  startBtn: HTMLElement | null;
  stopBtn: HTMLElement | null;
  messageId: string;
  private _showMessage: (elementId: string, type: string, text: string) => void;
  textFormat: (current: number, total: number, percent: number) => string;

  constructor(opts: ProgressTrackerOptions) {
    this.progressContainer = document.getElementById(opts.progressContainerId);
    this.fill = document.getElementById(opts.fillId);
    this.text = document.getElementById(opts.textId);
    this.startBtn = document.getElementById(opts.startBtnId);
    this.stopBtn = opts.stopBtnId ? document.getElementById(opts.stopBtnId) : null;
    this.messageId = opts.messageId;
    this._showMessage = opts.showMessage;
    this.textFormat = opts.textFormat ?? ((current, total, percent) => `${current}/${total} (${percent}%)`);
  }

  show(job: ProgressJob | null): void {
    this.progressContainer?.classList.remove('hidden');
    this.startBtn?.classList.add('hidden');
    if (this.stopBtn) this.stopBtn.classList.remove('hidden');

    if (job && job.progress_total > 0) {
      this.updateProgress(
        job.progress_current,
        job.progress_total,
        Math.round((job.progress_current / job.progress_total) * 100),
      );
    }
  }

  hide(): void {
    this.progressContainer?.classList.add('hidden');
    this.startBtn?.classList.remove('hidden');
    if (this.stopBtn) this.stopBtn.classList.add('hidden');
  }

  updateProgress(current: number, total: number, percent: number): void {
    if (this.fill) this.fill.style.width = percent + '%';
    if (this.text) this.text.textContent = this.textFormat(current, total, percent);
  }

  showMessage(type: string, text: string): void {
    this._showMessage(this.messageId, type, text);
  }
}
