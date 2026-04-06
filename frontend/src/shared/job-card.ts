import { ProgressTracker } from './progress-tracker';

export interface JobCardOptions {
  progressContainerId: string;
  fillId: string;
  textId: string;
  startBtnId: string;
  stopBtnId?: string | null;
  messageId: string;
  showMessage: (elementId: string, type: string, text: string) => void;
  textFormat?: ((current: number, total: number, percent: number) => string) | null;
  pendingCountId?: string | null;
  fetchPending?: (() => Promise<Record<string, unknown>>) | null;
  pendingField?: string;
  pendingMessageKey?: string | null;
  fetchStatus: () => Promise<Record<string, unknown>>;
  startJob: () => Promise<Record<string, unknown>>;
  stopJob?: ((jobId: string) => Promise<unknown>) | null;
  startedMessage?: string;
  completedMessage?: string;
  failedPrefix?: string;
  onComplete?: (() => void) | null;
}

export interface JobProgressData {
  job_id: string;
  current: number;
  total: number;
  percent: number;
}

export interface JobStatusData {
  job_id: string;
  status: string;
  error_message?: string;
}

export class JobCard {
  jobId: string | null = null;
  tracker: ProgressTracker;

  private _showMessage: (elementId: string, type: string, text: string) => void;
  private messageId: string;
  private pendingCountId: string | null;
  private fetchPending: (() => Promise<Record<string, unknown>>) | null;
  private pendingField: string;
  private pendingMessageKey: string | null;
  private fetchStatus: () => Promise<Record<string, unknown>>;
  private startJob: () => Promise<Record<string, unknown>>;
  private stopJob: ((jobId: string) => Promise<unknown>) | null;
  private startedMessage: string;
  private completedMessage: string;
  private failedPrefix: string;
  private onComplete: (() => void) | null;

  constructor(opts: JobCardOptions) {
    this._showMessage = opts.showMessage;
    this.messageId = opts.messageId;
    this.pendingCountId = opts.pendingCountId ?? null;
    this.fetchPending = opts.fetchPending ?? null;
    this.pendingField = opts.pendingField ?? 'pending_count';
    this.pendingMessageKey = opts.pendingMessageKey ?? null;
    this.fetchStatus = opts.fetchStatus;
    this.startJob = opts.startJob;
    this.stopJob = opts.stopJob ?? null;
    this.startedMessage = opts.startedMessage ?? 'Job started!';
    this.completedMessage = opts.completedMessage ?? 'Job completed!';
    this.failedPrefix = opts.failedPrefix ?? 'Job failed: ';
    this.onComplete = opts.onComplete ?? null;

    this.tracker = new ProgressTracker({
      progressContainerId: opts.progressContainerId,
      fillId: opts.fillId,
      textId: opts.textId,
      startBtnId: opts.startBtnId,
      stopBtnId: opts.stopBtnId,
      messageId: opts.messageId,
      showMessage: opts.showMessage,
      textFormat: opts.textFormat,
    });
  }

  async loadStatus(): Promise<void> {
    try {
      if (this.fetchPending && this.pendingCountId) {
        const pending = await this.fetchPending();
        const count = (pending[this.pendingField] as number) || 0;
        const el = document.getElementById(this.pendingCountId);
        if (el) {
          el.textContent = this.pendingMessageKey
            ? t(this.pendingMessageKey, { count })
            : String(count);
        }
      }

      const status = await this.fetchStatus();

      if (status.status === 'running') {
        this.jobId = status.job_id as string;
        this.tracker.show(status as unknown as { progress_current: number; progress_total: number });
      } else {
        this.tracker.hide();
      }
    } catch (err) {
      console.error(`Failed to load status for ${this.messageId}:`, err);
    }
  }

  async start(): Promise<void> {
    try {
      const data = await this.startJob();
      this.jobId = data.job_id as string;
      this._showMessage(this.messageId, 'success', this.startedMessage);
      this.tracker.show(null);
    } catch (err) {
      this._showMessage(this.messageId, 'error', this.failedPrefix + (err as Error).message);
    }
  }

  async stop(refreshCallback?: () => void): Promise<void> {
    if (!this.jobId || !this.stopJob) return;

    try {
      await this.stopJob(this.jobId);
      this._showMessage(this.messageId, 'success', 'Stopped!');
      this.tracker.hide();
      this.jobId = null;
      if (refreshCallback) refreshCallback();
      this.loadStatus();
    } catch (err) {
      this._showMessage(this.messageId, 'error', 'Failed to stop: ' + (err as Error).message);
    }
  }

  handleStatusChange(data: JobStatusData): boolean {
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

  handleProgress(data: JobProgressData): boolean {
    if (data.job_id !== this.jobId) return false;
    this.tracker.updateProgress(data.current, data.total, data.percent);
    return true;
  }
}
