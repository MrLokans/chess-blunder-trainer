import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import { client } from '../shared/api';
import { Alert } from '../components/Alert';
import { debounce } from '../shared/debounce';
import type { ExternalJobStatus } from '../components/JobCard';

interface ConfiguredUsernames {
  lichess_username?: string;
  chesscom_username?: string;
}

export type { ConfiguredUsernames };

const STORAGE_KEYS = {
  source: 'blunder_import_source',
  username: 'blunder_import_username',
  maxGames: 'blunder_import_maxGames',
} as const;

export { STORAGE_KEYS as IMPORT_STORAGE_KEYS };

interface ImportSectionProps {
  demoMode: boolean;
  configuredUsernames: ConfiguredUsernames;
  onImportStarted: (jobId: string) => void;
  importJobStatus: ExternalJobStatus | undefined;
}

export function ImportSection({ demoMode, configuredUsernames, onImportStarted, importJobStatus }: ImportSectionProps) {
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
              onInput={(e) => { setMaxGames((e.currentTarget).value); }}
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
