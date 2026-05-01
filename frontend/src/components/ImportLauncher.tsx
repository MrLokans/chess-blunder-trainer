import { useEffect, useRef, useState } from 'preact/hooks';
import { ApiError, client } from '../shared/api';
import type { Profile } from '../types/profiles';
import { Alert } from './Alert';
import { Button } from './Button';
import { ProgressBar } from './ProgressBar';
import type { ExternalJobStatus } from './JobCard';

export interface ImportLauncherProps {
  profile: Profile;
  demoMode?: boolean;
  externalStatus?: ExternalJobStatus;
  onImportStarted: (jobId: string) => void;
}

interface Status {
  type: 'success' | 'error';
  text: string;
}

export function ImportLauncher({
  profile,
  demoMode = false,
  externalStatus,
  onImportStarted,
}: ImportLauncherProps) {
  const [dispatching, setDispatching] = useState(false);
  const [progress, setProgress] = useState<{ current: number; total: number } | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const currentJobIdRef = useRef<string | null>(null);

  // The selected profile can change while a job is mid-flight (user picks a
  // different profile in the BulkImportPanel selector). Reset our local
  // job-tracking state so we don't leak a previous profile's progress into
  // the new launcher view.
  useEffect(() => {
    setProgress(null);
    setStatus(null);
    currentJobIdRef.current = null;
  }, [profile.id]);

  useEffect(() => {
    if (!externalStatus) return;
    if (externalStatus.job_id !== currentJobIdRef.current) return;

    if (externalStatus.status === 'completed') {
      setProgress(null);
      currentJobIdRef.current = null;
      setStatus({ type: 'success', text: t('management.import.completed') });
    } else if (externalStatus.status === 'failed') {
      setProgress(null);
      currentJobIdRef.current = null;
      setStatus({
        type: 'error',
        text: t('management.import.failed', {
          error: externalStatus.error_message ?? t('common.unknown_error'),
        }),
      });
    } else if (externalStatus.current != null && externalStatus.total != null) {
      setProgress({ current: externalStatus.current, total: externalStatus.total });
    }
  }, [externalStatus]);

  async function handleRun() {
    setStatus(null);
    setDispatching(true);
    try {
      const resp = await client.profiles.sync(profile.id);
      currentJobIdRef.current = resp.job_id;
      setProgress(null);
      setStatus({ type: 'success', text: t('management.import.started') });
      onImportStarted(resp.job_id);
    } catch (err) {
      const msg = err instanceof ApiError || err instanceof Error
        ? err.message
        : t('common.error');
      setStatus({
        type: 'error',
        text: t('management.import.start_failed', { error: msg }),
      });
    } finally {
      setDispatching(false);
    }
  }

  const maxGames = profile.preferences.sync_max_games;
  const lastSync = profile.last_game_sync_at;
  const isRunning = currentJobIdRef.current !== null;
  const editPrefsHref = `/profiles?profile_id=${String(profile.id)}&tab=preferences`;

  return (
    <div class="import-launcher">
      <dl class="import-launcher__prefs">
        <div class="import-launcher__prefs-row">
          <dt>{t('profiles.preferences.max_games')}</dt>
          <dd>{maxGames ?? t('profiles.preferences.use_global')}</dd>
        </div>
        <div class="import-launcher__prefs-row">
          <dt>{t('profiles.overview.last_game_sync')}</dt>
          <dd>{lastSync ?? t('profiles.list.never_synced')}</dd>
        </div>
      </dl>

      {status && <Alert type={status.type} message={status.text} />}

      {isRunning && progress && (
        <ProgressBar current={progress.current} total={progress.total} />
      )}

      <div class="import-launcher__actions">
        <Button
          variant="primary"
          onClick={() => { void handleRun(); }}
          loading={dispatching || isRunning}
          disabled={demoMode}
        >
          {t('profiles.bulk_import.run_button')}
        </Button>
        <a class="import-launcher__edit-link" href={editPrefsHref}>
          {t('profiles.bulk_import.edit_preferences')}
        </a>
      </div>
    </div>
  );
}
