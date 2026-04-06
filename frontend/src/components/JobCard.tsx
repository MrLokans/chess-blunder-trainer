import { useState, useEffect, useCallback } from 'preact/hooks';
import { ProgressBar } from './ProgressBar';
import { Alert } from './Alert';

interface JobStatus {
  status: string;
  job_id?: string;
  progress_current?: number;
  progress_total?: number;
}

export interface ExternalJobStatus {
  job_id: string;
  status: string;
  error_message?: string;
  current?: number;
  total?: number;
  percent?: number;
}

interface JobCardProps {
  fetchStatus: () => Promise<JobStatus>;
  startJob: () => Promise<{ job_id: string }>;
  stopJob?: (jobId: string) => Promise<unknown>;
  startedMessage?: string;
  completedMessage?: string;
  failedPrefix?: string;
  onComplete?: () => void;
  textFormat?: (current: number, total: number) => string;
  externalStatus?: ExternalJobStatus;
  startLabel?: string;
  stopLabel?: string;
}

export function JobCard({
  fetchStatus,
  startJob,
  stopJob,
  startedMessage = 'Job started!',
  completedMessage = 'Job completed!',
  failedPrefix = 'Job failed: ',
  onComplete,
  textFormat,
  externalStatus,
  startLabel = 'Start',
  stopLabel = 'Stop',
}: JobCardProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const loadStatus = useCallback(async () => {
    try {
      const status = await fetchStatus();
      if (status.status === 'running' && status.job_id) {
        setJobId(status.job_id);
        setCurrent(status.progress_current ?? 0);
        setTotal(status.progress_total ?? 0);
      } else {
        setJobId(null);
      }
    } catch (err) {
      console.error('Failed to load job status:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchStatus]);

  useEffect(() => {
    void loadStatus();
  }, [loadStatus]);

  useEffect(() => {
    if (!externalStatus || externalStatus.job_id !== jobId) return;

    if (externalStatus.status === 'completed') {
      setJobId(null);
      setMessage({ type: 'success', text: completedMessage });
      if (onComplete) onComplete();
    } else if (externalStatus.status === 'failed') {
      setJobId(null);
      setMessage({ type: 'error', text: failedPrefix + (externalStatus.error_message ?? 'Unknown error') });
    } else if (externalStatus.current != null && externalStatus.total != null) {
      setCurrent(externalStatus.current);
      setTotal(externalStatus.total);
    }
  }, [externalStatus, jobId, completedMessage, failedPrefix, onComplete]);

  const handleStart = useCallback(async () => {
    try {
      const data = await startJob();
      setJobId(data.job_id);
      setCurrent(0);
      setTotal(0);
      setMessage({ type: 'success', text: startedMessage });
    } catch (err) {
      setMessage({ type: 'error', text: failedPrefix + (err as Error).message });
    }
  }, [startJob, startedMessage, failedPrefix]);

  const handleStop = useCallback(async () => {
    if (!jobId || !stopJob) return;
    try {
      await stopJob(jobId);
      setJobId(null);
      setMessage({ type: 'success', text: 'Stopped!' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to stop: ' + (err as Error).message });
    }
  }, [jobId, stopJob]);

  if (loading) return null;

  return (
    <div class="job-card">
      <Alert type={message?.type ?? 'success'} message={message?.text ?? null} />
      {jobId ? (
        <>
          <ProgressBar current={current} total={total} textFormat={textFormat} />
          {stopJob && (
            <button type="button" class="btn btn-danger" onClick={() => { void handleStop(); }}>
              {stopLabel}
            </button>
          )}
        </>
      ) : (
        <button type="button" class="btn btn-primary" onClick={() => { void handleStart(); }}>
          {startLabel}
        </button>
      )}
    </div>
  );
}
