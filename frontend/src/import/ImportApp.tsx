import { useState } from 'preact/hooks';
import { client, ApiError } from '../shared/api';
import type { ImportResult } from '../types/api';

interface Props {
  demoMode: boolean;
}

const POLL_INTERVAL_MS = 1500;

export function ImportApp({ demoMode }: Props) {
  const [pgn, setPgn] = useState('');
  const [errors, setErrors] = useState<string[] | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);

  async function pollJob(jobId: string): Promise<void> {
    try {
      const job = await client.jobs.getImportStatus(jobId);
      if (job.status === 'completed') {
        setResult(job.result ?? {});
        setAnalyzing(false);
      } else if (job.status === 'failed') {
        setErrors([job.error_message ?? t('import.analyzing')]);
        setAnalyzing(false);
      } else {
        setTimeout(() => pollJob(jobId), POLL_INTERVAL_MS);
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : t('common.error');
      setErrors([msg]);
      setAnalyzing(false);
    }
  }

  async function handleSubmit(): Promise<void> {
    const trimmed = pgn.trim();
    if (!trimmed) return;

    setErrors(null);
    setResult(null);
    setAnalyzing(true);

    try {
      const data = await client.importPgn(trimmed);
      if (!data.success) {
        setErrors(data.errors ?? [t('common.error')]);
        setAnalyzing(false);
        return;
      }
      if (data.job_id) {
        pollJob(data.job_id);
      } else {
        setAnalyzing(false);
      }
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : (err instanceof Error ? err.message : t('common.error'));
      setErrors([msg]);
      setAnalyzing(false);
    }
  }

  const ecoText = result
    ? ([result.eco_code, result.eco_name].filter(Boolean).join(' \u2014 ') || '\u2014')
    : null;

  return (
    <div>
      <p class="import-description">{t('import.description')}</p>

      <div class="import-form">
        <textarea
          class="pgn-textarea"
          rows={14}
          placeholder={t('import.placeholder')}
          value={pgn}
          onInput={(e) => setPgn(e.currentTarget.value)}
          disabled={analyzing}
        />

        {errors && (
          <div class="import-errors">
            <ul>
              {errors.map((err, i) => <li key={i}>{err}</li>)}
            </ul>
          </div>
        )}

        {!demoMode && (
          <button
            class="btn btn-primary"
            onClick={handleSubmit}
            disabled={analyzing || !pgn.trim()}
          >
            {t('import.submit')}
          </button>
        )}

        {analyzing && (
          <div class="import-spinner">
            <span class="spinner" />
            <span>{t('import.analyzing')}</span>
          </div>
        )}
      </div>

      {result && (
        <div class="import-results">
          <h2>{t('import.success')}</h2>
          <div class="results-grid">
            <div class="result-item">
              <span class="result-label">{t('import.results.eco')}</span>
              <span class="result-value">{ecoText}</span>
            </div>
            <div class="result-item">
              <span class="result-label">{t('import.results.moves')}</span>
              <span class="result-value">{result.total_moves ?? 0}</span>
            </div>
            <div class="result-item result-blunders">
              <span class="result-label">{t('import.results.blunders')}</span>
              <span class="result-value">{result.blunders ?? 0}</span>
            </div>
            <div class="result-item result-mistakes">
              <span class="result-label">{t('import.results.mistakes')}</span>
              <span class="result-value">{result.mistakes ?? 0}</span>
            </div>
            <div class="result-item result-inaccuracies">
              <span class="result-label">{t('import.results.inaccuracies')}</span>
              <span class="result-value">{result.inaccuracies ?? 0}</span>
            </div>
          </div>
          <a href="/" class="btn btn-secondary">{t('import.results.go_to_trainer')}</a>
        </div>
      )}
    </div>
  );
}
