const btn = document.getElementById('importBtn') as HTMLButtonElement | null;
const input = document.getElementById('pgnInput') as HTMLTextAreaElement | null;
const errorsEl = document.getElementById('importErrors');
const spinner = document.getElementById('importSpinner');
const results = document.getElementById('importResults');

if (btn && input) {
  const POLL_INTERVAL_MS = 1500;
  const importBtn = btn;

  importBtn.addEventListener('click', async () => {
    const pgn = input.value.trim();
    if (!pgn) return;

    errorsEl?.classList.add('hidden');
    results?.classList.add('hidden');
    spinner?.classList.remove('hidden');
    importBtn.disabled = true;

    try {
      const resp = await fetch('/api/import/pgn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pgn }),
      });

      const data = await resp.json() as {
        success?: boolean;
        job_id?: string;
        errors?: string[];
        detail?: string;
      };

      if (!resp.ok || !data.success) {
        showErrors(data.errors || [data.detail || 'Unknown error']);
        spinner?.classList.add('hidden');
        importBtn.disabled = false;
        return;
      }

      pollJob(data.job_id!);
    } catch (e) {
      showErrors([(e as Error).message || 'Network error']);
      spinner?.classList.add('hidden');
      importBtn.disabled = false;
    }
  });

  async function pollJob(jobId: string): Promise<void> {
    try {
      const resp = await fetch('/api/import/status/' + encodeURIComponent(jobId));
      if (!resp.ok) {
        showErrors(['Failed to check analysis status']);
        done();
        return;
      }

      const job = await resp.json() as {
        status: string;
        result?: ImportResult;
        error_message?: string;
      };

      if (job.status === 'completed') {
        showResults(job.result ?? {});
        done();
      } else if (job.status === 'failed') {
        showErrors([job.error_message || 'Analysis failed']);
        done();
      } else {
        setTimeout(() => pollJob(jobId), POLL_INTERVAL_MS);
      }
    } catch (e) {
      showErrors([(e as Error).message || 'Network error']);
      done();
    }
  }

  function done(): void {
    spinner?.classList.add('hidden');
    importBtn.disabled = false;
  }

  function showErrors(errors: string[]): void {
    if (!errorsEl) return;
    errorsEl.innerHTML = '<ul>' + errors.map(e => '<li>' + escapeHtml(e) + '</li>').join('') + '</ul>';
    errorsEl.classList.remove('hidden');
  }

  interface ImportResult {
    eco_code?: string;
    eco_name?: string;
    total_moves?: number;
    blunders?: number;
    mistakes?: number;
    inaccuracies?: number;
  }

  function showResults(data: ImportResult): void {
    const ecoText = [data.eco_code, data.eco_name].filter(Boolean).join(' \u2014 ') || '\u2014';
    const resEco = document.getElementById('resEco');
    const resMoves = document.getElementById('resMoves');
    const resBlunders = document.getElementById('resBlunders');
    const resMistakes = document.getElementById('resMistakes');
    const resInaccuracies = document.getElementById('resInaccuracies');
    if (resEco) resEco.textContent = ecoText;
    if (resMoves) resMoves.textContent = String(data.total_moves || 0);
    if (resBlunders) resBlunders.textContent = String(data.blunders || 0);
    if (resMistakes) resMistakes.textContent = String(data.mistakes || 0);
    if (resInaccuracies) resInaccuracies.textContent = String(data.inaccuracies || 0);
    results?.classList.remove('hidden');
  }

  function escapeHtml(str: string): string {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
}
