import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import { client } from '../shared/api';
import { JobCard } from '../components/JobCard';
import { Alert } from '../components/Alert';
import { useWebSocket } from '../hooks/useWebSocket';
import { debounce } from '../shared/debounce';
import type { ExternalJobStatus } from '../components/JobCard';

interface ManagementInit {
  demoMode: boolean;
}

interface EngineStatus {
  available: boolean;
  name?: string;
  path?: string;
}

interface ConfiguredUsernames {
  lichess_username?: string;
  chesscom_username?: string;
}

const STORAGE_KEYS = {
  source: 'blunder_import_source',
  username: 'blunder_import_username',
  maxGames: 'blunder_import_maxGames',
} as const;

const APP_STORAGE_KEYS = [
  STORAGE_KEYS.source,
  STORAGE_KEYS.username,
  STORAGE_KEYS.maxGames,
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
  APP_STORAGE_KEYS.forEach(key => localStorage.removeItem(key));
}

function EngineStatusSection() {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await client.system.engineStatus();
        setStatus(data);
      } catch (err) {
        const msg = err instanceof Error ? err.message : t('common.error');
        setError(t('management.engine.load_failed', { error: msg }));
      }
    }
    void load();
  }, []);

  if (error) {
    return (
      <div style="display: flex; align-items: center; gap: 8px;">
        <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--error);" />
        <span style="color: var(--error);">{error}</span>
      </div>
    );
  }

  if (!status) {
    return <p class="section-description">{t('management.engine.loading')}</p>;
  }

  if (status.available) {
    return (
      <div>
        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
          <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--success);" />
          <span style="font-weight: 600; color: var(--success);">{t('management.engine.available')}</span>
        </div>
        <table style="font-size: 0.875rem; color: var(--text-muted);">
          <tr>
            <td style="padding-right: 16px;">{t('management.engine.name')}</td>
            <td style="font-family: monospace;">{status.name ?? t('common.unknown')}</td>
          </tr>
          <tr>
            <td style="padding-right: 16px;">{t('management.engine.path')}</td>
            <td style="font-family: monospace;">{status.path ?? t('common.unknown')}</td>
          </tr>
        </table>
      </div>
    );
  }

  return (
    <div>
      <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
        <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: var(--error);" />
        <span style="font-weight: 600; color: var(--error);">{t('management.engine.unavailable')}</span>
      </div>
      <p style="color: var(--text-muted); font-size: 0.875rem;">
        {t('management.engine.path')} <code>{status.path ?? t('management.engine.not_configured')}</code>
        <br />
        {t('management.engine.install_hint')}
      </p>
    </div>
  );
}

interface ImportSectionProps {
  demoMode: boolean;
  configuredUsernames: ConfiguredUsernames;
  onImportStarted: (jobId: string) => void;
  importJobStatus: ExternalJobStatus | undefined;
}

function ImportSection({ demoMode, configuredUsernames, onImportStarted, importJobStatus }: ImportSectionProps) {
  const [source, setSource] = useState(() => localStorage.getItem(STORAGE_KEYS.source) ?? '');
  const [username, setUsername] = useState(() => localStorage.getItem(STORAGE_KEYS.username) ?? '');
  const [maxGames, setMaxGames] = useState(() => localStorage.getItem(STORAGE_KEYS.maxGames) ?? '1000');
  const [usernameValid, setUsernameValid] = useState<boolean | null>(null);
  const [validationState, setValidationState] = useState<'idle' | 'checking' | 'valid' | 'invalid'>('idle');
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);
  const [importing, setImporting] = useState(false);
  const [importProgress, setImportProgress] = useState<{ current: number; total: number } | null>(null);
  const currentJobIdRef = useRef<string | null>(null);

  useEffect(() => {
    if (!source || username) return;
    if (source === 'lichess' && configuredUsernames.lichess_username) {
      setUsername(configuredUsernames.lichess_username);
    } else if (source === 'chesscom' && configuredUsernames.chesscom_username) {
      setUsername(configuredUsernames.chesscom_username);
    }
  }, [source, configuredUsernames]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.source, source);
  }, [source]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.username, username);
  }, [username]);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEYS.maxGames, maxGames);
  }, [maxGames]);

  const validateUsername = useCallback(async (src: string, uname: string) => {
    if (!src || !uname) {
      setUsernameValid(null);
      setValidationState('idle');
      return;
    }
    setValidationState('checking');
    try {
      const result = await client.setup.validateUsername(src, uname);
      setUsernameValid(result.valid);
      setValidationState(result.valid ? 'valid' : 'invalid');
    } catch {
      setUsernameValid(null);
      setValidationState('idle');
    }
  }, []);

  const debouncedValidate = useCallback(
    debounce((src: string, uname: string) => { void validateUsername(src, uname); }, 500),
    [validateUsername],
  );

  const handleSourceChange = (e: Event) => {
    const val = (e.currentTarget as HTMLSelectElement).value;
    setSource(val);
    setUsernameValid(null);
    if (username) {
      debouncedValidate(val, username);
    }
  };

  const handleUsernameChange = (e: Event) => {
    const val = (e.currentTarget as HTMLInputElement).value;
    setUsername(val);
    setUsernameValid(null);
    if (val) {
      setValidationState('checking');
      debouncedValidate(source, val);
    } else {
      setValidationState('idle');
    }
  };

  useEffect(() => {
    if (!importJobStatus) return;
    if (importJobStatus.job_id !== currentJobIdRef.current) return;

    if (importJobStatus.status === 'completed') {
      setImporting(false);
      setImportProgress(null);
      currentJobIdRef.current = null;
      setMessage({ type: 'success', text: t('management.import.completed') });
    } else if (importJobStatus.status === 'failed') {
      setImporting(false);
      setImportProgress(null);
      currentJobIdRef.current = null;
      setMessage({ type: 'error', text: t('management.import.failed', { error: importJobStatus.error_message ?? t('common.unknown_error') }) });
    } else if (importJobStatus.current != null && importJobStatus.total != null) {
      setImportProgress({ current: importJobStatus.current, total: importJobStatus.total });
    }
  }, [importJobStatus]);

  const handleSubmit = async (e: Event) => {
    e.preventDefault();

    if (usernameValid === null && source && username) {
      setValidationState('checking');
      try {
        const result = await client.setup.validateUsername(source, username);
        setUsernameValid(result.valid);
        setValidationState(result.valid ? 'valid' : 'invalid');
      } catch {
        setUsernameValid(null);
        setValidationState('idle');
      }
    }

    if (usernameValid === false) {
      setMessage({ type: 'error', text: t('setup.username_invalid') });
      return;
    }

    try {
      const data = await client.jobs.startImport(source, username, parseInt(maxGames));
      currentJobIdRef.current = data.job_id;
      onImportStarted(data.job_id);
      setImporting(true);
      setImportProgress(null);
      setMessage({ type: 'success', text: t('management.import.started') });
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('common.error');
      setMessage({ type: 'error', text: t('management.import.start_failed', { error: msg }) });
    }
  };

  const percent = importProgress && importProgress.total > 0
    ? Math.round((importProgress.current / importProgress.total) * 100)
    : 0;

  return (
    <section>
      <h2>{t('management.import.title')}</h2>
      <Alert type={message?.type ?? 'success'} message={message?.text ?? null} />

      {demoMode ? (
        <p class="section-description">{t('demo.disabled_action')}</p>
      ) : (
        <form onSubmit={(e) => { void handleSubmit(e); }}>
          <div class="form-group">
            <label for="source">{t('management.import.source')}</label>
            <select id="source" required value={source} onChange={handleSourceChange}>
              <option value="">{t('management.import.select_source')}</option>
              <option value="lichess">{t('management.import.lichess')}</option>
              <option value="chesscom">{t('management.import.chesscom')}</option>
            </select>
          </div>
          <div class="form-group">
            <label for="username">{t('management.import.username')}</label>
            <input
              type="text"
              id="username"
              required
              placeholder={t('management.import.username_placeholder')}
              value={username}
              onInput={handleUsernameChange}
            />
            {validationState !== 'idle' && (
              <span class={`field-validation ${validationState}`}>
                {validationState === 'checking' && t('setup.validating')}
                {validationState === 'valid' && t('setup.username_valid')}
                {validationState === 'invalid' && t('setup.username_invalid')}
              </span>
            )}
          </div>
          <div class="form-group">
            <label for="maxGames">{t('management.import.max_games')}</label>
            <input
              type="number"
              id="maxGames"
              min="1"
              max="10000"
              value={maxGames}
              onInput={(e) => setMaxGames((e.currentTarget as HTMLInputElement).value)}
            />
          </div>
          <button type="submit" class="btn">{t('management.import.start')}</button>
        </form>
      )}

      {importing && (
        <div class="progress-section">
          <p><strong>{t('management.import.in_progress')}</strong></p>
          <div class="progress-bar">
            <div class="progress-fill" style={{ width: `${String(percent)}%` }} />
            <div class="progress-text">
              {importProgress
                ? `${String(importProgress.current)}/${String(importProgress.total)} (${String(percent)}%)`
                : '0%'}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

interface SyncSectionProps {
  demoMode: boolean;
}

function SyncSection({ demoMode }: SyncSectionProps) {
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);

  const handleSync = async () => {
    try {
      await client.jobs.startSync();
      setMessage({ type: 'success', text: t('management.sync.started') });
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('common.error');
      setMessage({ type: 'error', text: t('management.sync.failed', { error: msg }) });
    }
  };

  return (
    <section>
      <h2>{t('management.sync.title')}</h2>
      <p class="section-description mb-4">{t('management.sync.description')}</p>
      {demoMode ? (
        <p class="section-description">{t('demo.disabled_action')}</p>
      ) : (
        <button class="btn" type="button" onClick={() => { void handleSync(); }}>
          {t('management.sync.button')}
        </button>
      )}
      {message && (
        <div class={`message ${message.type} mt-4`}>{message.text}</div>
      )}
    </section>
  );
}

interface JobsSectionProps {
  jobsRefreshKey: number;
}

function JobsSection({ jobsRefreshKey }: JobsSectionProps) {
  const tbodyRef = useRef<HTMLTableSectionElement | null>(null);

  useEffect(() => {
    const el = tbodyRef.current;
    if (!el) return;
    htmx.process(el);
  }, []);

  useEffect(() => {
    if (jobsRefreshKey > 0) {
      htmx.trigger(document.body, 'jobsRefresh');
    }
  }, [jobsRefreshKey]);

  return (
    <section>
      <h2>{t('management.jobs.title')}</h2>
      <div class="table-scroll">
        <table id="jobsTable">
          <thead>
            <tr>
              <th>{t('management.jobs.type')}</th>
              <th>{t('management.jobs.status')}</th>
              <th>{t('management.jobs.username')}</th>
              <th>{t('management.jobs.source')}</th>
              <th>{t('management.jobs.progress')}</th>
              <th>{t('management.jobs.created')}</th>
              <th>{t('management.jobs.actions')}</th>
            </tr>
          </thead>
          <tbody
            ref={tbodyRef}
            id="jobsTableBody"
            hx-get="/api/jobs/html"
            hx-trigger="load, jobsRefresh from:body"
            hx-swap="innerHTML"
          >
            <tr>
              <td colspan={7} class="table-placeholder">{t('common.loading')}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}

interface DangerSectionProps {
  externalStatus?: ExternalJobStatus;
}

function DangerSection({ externalStatus }: DangerSectionProps) {
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
      setTimeout(() => window.location.reload(), 2000);
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

export function ManagementApp({ demoMode }: ManagementInit) {
  const [configuredUsernames, setConfiguredUsernames] = useState<ConfiguredUsernames>({});
  const [importJobId, setImportJobId] = useState<string | null>(null);
  const [jobsRefreshKey, setJobsRefreshKey] = useState(0);

  const [analysisStatus, setAnalysisStatus] = useState<ExternalJobStatus | undefined>(undefined);
  const [backfillStatus, setBackfillStatus] = useState<ExternalJobStatus | undefined>(undefined);
  const [ecoBackfillStatus, setEcoBackfillStatus] = useState<ExternalJobStatus | undefined>(undefined);
  const [trapsBackfillStatus, setTrapsBackfillStatus] = useState<ExternalJobStatus | undefined>(undefined);
  const [deleteAllStatus, setDeleteAllStatus] = useState<ExternalJobStatus | undefined>(undefined);
  const [importStatus, setImportStatus] = useState<ExternalJobStatus | undefined>(undefined);

  useEffect(() => {
    async function load() {
      try {
        const usernames = await client.settings.getUsernames();
        setConfiguredUsernames(usernames);
      } catch (err) {
        console.error('Failed to load configured usernames:', err);
      }
    }
    void load();
  }, []);

  const debouncedRefresh = useCallback(
    debounce(() => setJobsRefreshKey(k => k + 1), 1000),
    [],
  );

  const { on } = useWebSocket([
    'job.created',
    'job.status_changed',
    'job.progress_updated',
    'job.completed',
    'job.failed',
  ]);

  useEffect(() => {
    const unsubProgress = on('job.progress_updated', (raw) => {
      const data = raw as { job_id: string; current: number; total: number; percent: number };
      const ext: ExternalJobStatus = {
        job_id: data.job_id,
        status: 'running',
        current: data.current,
        total: data.total,
        percent: data.percent,
      };

      if (data.job_id === importJobId) {
        setImportStatus(ext);
      }
      setAnalysisStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setBackfillStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setEcoBackfillStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setTrapsBackfillStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setDeleteAllStatus(prev => prev?.job_id === data.job_id ? ext : prev);

      debouncedRefresh();
    });

    const unsubStatus = on('job.status_changed', (raw) => {
      const data = raw as { job_id: string; status: string; error_message?: string };
      const ext: ExternalJobStatus = {
        job_id: data.job_id,
        status: data.status as ExternalJobStatus['status'],
        error_message: data.error_message,
      };

      if (data.job_id === importJobId) {
        setImportStatus(ext);
      }
      setAnalysisStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setBackfillStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setEcoBackfillStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setTrapsBackfillStatus(prev => prev?.job_id === data.job_id ? ext : prev);
      setDeleteAllStatus(prev => prev?.job_id === data.job_id ? ext : prev);

      setJobsRefreshKey(k => k + 1);
    });

    const unsubCreated = on('job.created', () => {
      setJobsRefreshKey(k => k + 1);
    });

    return () => {
      unsubProgress();
      unsubStatus();
      unsubCreated();
    };
  }, [on, importJobId, debouncedRefresh]);

  const handleImportStarted = useCallback((jobId: string) => {
    setImportJobId(jobId);
    setImportStatus({ job_id: jobId, status: 'running' });
  }, []);

  return (
    <div>
      <section>
        <h2>{t('management.engine.title')}</h2>
        <EngineStatusSection />
      </section>

      <hr class="section-divider" />

      <ImportSection
        demoMode={demoMode}
        configuredUsernames={configuredUsernames}
        onImportStarted={handleImportStarted}
        importJobStatus={importStatus}
      />

      <hr class="section-divider" />

      <SyncSection demoMode={demoMode} />

      <hr class="section-divider" />

      <section>
        <h2>{t('management.analysis.title')}</h2>
        <p class="section-description mb-4">{t('management.analysis.pending_desc')}</p>
        {!demoMode && (
          <JobCard
            fetchStatus={() => client.analysis.status()}
            startJob={() => client.analysis.start()}
            stopJob={(jobId) => client.analysis.stop(jobId)}
            startedMessage={t('management.analysis.started')}
            completedMessage={t('management.analysis.completed')}
            failedPrefix={t('management.analysis.failed', { error: '' })}
            externalStatus={analysisStatus}
            startLabel={t('management.analysis.start')}
            stopLabel={t('management.analysis.stop')}
          />
        )}
      </section>

      <hr class="section-divider" />

      <section>
        <h2>{t('management.backfill_phases.title')}</h2>
        <p class="section-description mb-4">{t('management.backfill_phases.description')}</p>
        {!demoMode && (
          <JobCard
            fetchStatus={() => client.backfill.phasesStatus()}
            startJob={() => client.backfill.startPhases()}
            startedMessage={t('management.backfill_phases.started')}
            completedMessage={t('management.backfill_phases.completed')}
            failedPrefix={t('management.backfill_phases.failed', { error: '' })}
            externalStatus={backfillStatus}
            startLabel={t('management.backfill_phases.start')}
          />
        )}
      </section>

      <hr class="section-divider" />

      <section>
        <h2>{t('management.backfill_eco.title')}</h2>
        <p class="section-description mb-4">{t('management.backfill_eco.description')}</p>
        {!demoMode && (
          <JobCard
            fetchStatus={() => client.backfill.ecoStatus()}
            startJob={() => client.backfill.startEco()}
            startedMessage={t('management.backfill_eco.started')}
            completedMessage={t('management.backfill_eco.completed')}
            failedPrefix={t('management.backfill_eco.failed', { error: '' })}
            externalStatus={ecoBackfillStatus}
            startLabel={t('management.backfill_eco.start')}
          />
        )}
      </section>

      <hr class="section-divider" />

      <section>
        <h2>{t('management.backfill_traps.title')}</h2>
        <p class="section-description mb-4">{t('management.backfill_traps.description')}</p>
        {!demoMode && (
          <JobCard
            fetchStatus={() => client.backfill.trapsStatus()}
            startJob={() => client.backfill.startTraps()}
            startedMessage={t('management.backfill_traps.started')}
            completedMessage={t('management.backfill_traps.completed')}
            failedPrefix={t('management.backfill_traps.failed', { error: '' })}
            externalStatus={trapsBackfillStatus}
            startLabel={t('management.backfill_traps.start')}
          />
        )}
      </section>

      <hr class="section-divider" />

      <JobsSection jobsRefreshKey={jobsRefreshKey} />

      {!demoMode && (
        <>
          <hr class="section-divider" />
          <DangerSection externalStatus={deleteAllStatus} />
        </>
      )}
    </div>
  );
}
