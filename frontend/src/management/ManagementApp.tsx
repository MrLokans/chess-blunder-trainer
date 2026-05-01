import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import { client } from '../shared/api';
import { BulkImportPanel } from '../components/BulkImportPanel';
import { JobCard } from '../components/JobCard';
import { useWebSocket } from '../hooks/useWebSocket';
import { debounce } from '../shared/debounce';
import type { ExternalJobStatus } from '../components/JobCard';
import type { Profile } from '../types/profiles';
import { DangerSection } from './DangerSection';

interface ManagementInit {
  demoMode: boolean;
}

interface EngineStatus {
  available: boolean;
  name?: string;
  path?: string;
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
      <div class="engine-status-row">
        <span class="status-dot status-dot--error" />
        <span class="text-error">{error}</span>
      </div>
    );
  }

  if (!status) {
    return <p class="section-description">{t('management.engine.loading')}</p>;
  }

  if (status.available) {
    return (
      <div>
        <div class="engine-status-row">
          <span class="status-dot status-dot--success" />
          <span class="text-success font-semibold">{t('management.engine.available')}</span>
        </div>
        <table class="engine-details">
          <tr>
            <td>{t('management.engine.name')}</td>
            <td class="font-mono">{status.name ?? t('common.unknown')}</td>
          </tr>
          <tr>
            <td>{t('management.engine.path')}</td>
            <td class="font-mono">{status.path ?? t('common.unknown')}</td>
          </tr>
        </table>
      </div>
    );
  }

  return (
    <div>
      <div class="engine-status-row">
        <span class="status-dot status-dot--error" />
        <span class="text-error font-semibold">{t('management.engine.unavailable')}</span>
      </div>
      <p class="section-description">
        {t('management.engine.path')} <code>{status.path ?? t('management.engine.not_configured')}</code>
        <br />
        {t('management.engine.install_hint')}
      </p>
    </div>
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

export function ManagementApp({ demoMode }: ManagementInit) {
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [profilesLoading, setProfilesLoading] = useState(true);
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
        const resp = await client.profiles.list();
        setProfiles(resp.profiles);
      } catch (err) {
        console.error('Failed to load profiles:', err);
      } finally {
        setProfilesLoading(false);
      }
    }
    void load();
  }, []);

  const debouncedRefresh = useCallback(
    debounce(() => { setJobsRefreshKey(k => k + 1); }, 1000),
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

      <section>
        <h2>{t('management.import.title')}</h2>
        {demoMode ? (
          <p class="section-description">{t('demo.disabled_action')}</p>
        ) : (
          <BulkImportPanel
            profiles={profiles}
            loading={profilesLoading}
            demoMode={demoMode}
            externalStatus={importStatus}
            onImportStarted={handleImportStarted}
          />
        )}
      </section>

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
          <div class="btn-row">
            <JobCard
              fetchStatus={() => client.backfill.ecoStatus()}
              startJob={() => client.backfill.startEco()}
              startedMessage={t('management.backfill_eco.started')}
              completedMessage={t('management.backfill_eco.completed')}
              failedPrefix={t('management.backfill_eco.failed', { error: '' })}
              externalStatus={ecoBackfillStatus}
              startLabel={t('management.backfill_eco.start')}
            />
            <JobCard
              fetchStatus={() => client.backfill.ecoStatus()}
              startJob={() => client.backfill.startEcoForce()}
              startedMessage={t('management.backfill_eco.started')}
              completedMessage={t('management.backfill_eco.completed')}
              failedPrefix={t('management.backfill_eco.failed', { error: '' })}
              externalStatus={ecoBackfillStatus}
              startLabel={t('management.backfill_eco.force_start')}
            />
          </div>
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
