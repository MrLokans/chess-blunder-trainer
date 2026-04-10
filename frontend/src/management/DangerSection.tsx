import { useState, useEffect, useCallback } from 'preact/hooks';
import { client } from '../shared/api';
import { Alert } from '../components/Alert';
import type { ExternalJobStatus } from '../components/JobCard';

const APP_STORAGE_KEYS = [
  'blunder_import_source',
  'blunder_import_username',
  'blunder_import_maxGames',
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
  APP_STORAGE_KEYS.forEach(key => { localStorage.removeItem(key); });
}

interface DangerSectionProps {
  externalStatus?: ExternalJobStatus;
}

export function DangerSection({ externalStatus }: DangerSectionProps) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [current, setCurrent] = useState(0);
  const [total, setTotal] = useState(0);
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);

  useEffect(() => {
    async function loadStatus() {
      try {
        const status = await client.data.deleteStatus();
        if (status.status === 'running' && status.job_id) {
          setJobId(status.job_id);
          setCurrent(status.progress_current ?? 0);
          setTotal(status.progress_total ?? 0);
        }
      } catch (err) {
        console.error('Failed to load delete status:', err);
      }
    }
    void loadStatus();
  }, []);

  useEffect(() => {
    if (!externalStatus || externalStatus.job_id !== jobId) return;

    if (externalStatus.status === 'completed') {
      setJobId(null);
      setMessage({ type: 'success', text: t('management.danger.completed') });
      clearAppLocalStorage();
      setTimeout(() => { window.location.reload(); }, 2000);
    } else if (externalStatus.status === 'failed') {
      setJobId(null);
      setMessage({ type: 'error', text: t('management.danger.failed', { error: '' }) + (externalStatus.error_message ?? t('common.unknown_error')) });
    } else if (externalStatus.current != null && externalStatus.total != null) {
      setCurrent(externalStatus.current);
      setTotal(externalStatus.total);
    }
  }, [externalStatus, jobId]);

  const handleDeleteAll = useCallback(async () => {
    if (!confirm(t('management.danger.confirm1'))) return;
    if (!confirm(t('management.danger.confirm2'))) return;

    try {
      const data = await client.data.deleteAll();
      setJobId(data.job_id);
      setCurrent(0);
      setTotal(0);
      setMessage({ type: 'success', text: t('management.danger.started') });
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('common.error');
      setMessage({ type: 'error', text: t('management.danger.failed', { error: '' }) + msg });
    }
  }, []);

  const percent = total > 0 ? Math.round((current / total) * 100) : 0;

  return (
    <section>
      <h2 class="danger-title">{t('management.danger.title')}</h2>
      <Alert type={message?.type ?? 'success'} message={message?.text ?? null} />
      <p class="section-description mb-4">
        {t('management.danger.description')}
        <strong>{t('management.danger.warning')}</strong> {t('management.danger.settings_preserved')}
      </p>
      {!jobId && (
        <button class="btn btn-danger" type="button" onClick={() => { void handleDeleteAll(); }}>
          {t('management.danger.button')}
        </button>
      )}
      {jobId && (
        <div class="progress-section">
          <p><strong>{t('management.danger.deleting')}</strong></p>
          <div class="progress-bar">
            <div class="progress-fill danger" style={{ width: `${String(percent)}%` }} />
            <div class="progress-text">{`${String(current)}/${String(total)} (${String(percent)}%)`}</div>
          </div>
        </div>
      )}
    </section>
  );
}
