(function () {
  const btn = document.getElementById('importBtn');
  const input = document.getElementById('pgnInput');
  const errorsEl = document.getElementById('importErrors');
  const spinner = document.getElementById('importSpinner');
  const results = document.getElementById('importResults');

  if (!btn) return;

  const POLL_INTERVAL_MS = 1500;

  btn.addEventListener('click', async () => {
    const pgn = input.value.trim();
    if (!pgn) return;

    errorsEl.classList.add('hidden');
    results.classList.add('hidden');
    spinner.classList.remove('hidden');
    btn.disabled = true;

    try {
      const resp = await fetch('/api/import/pgn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pgn }),
      });

      const data = await resp.json();

      if (!resp.ok || !data.success) {
        showErrors(data.errors || [data.detail || 'Unknown error']);
        spinner.classList.add('hidden');
        btn.disabled = false;
        return;
      }

      pollJob(data.job_id);
    } catch (e) {
      showErrors([e.message || 'Network error']);
      spinner.classList.add('hidden');
      btn.disabled = false;
    }
  });

  async function pollJob(jobId) {
    try {
      const resp = await fetch('/api/import/status/' + encodeURIComponent(jobId));
      if (!resp.ok) {
        showErrors(['Failed to check analysis status']);
        done();
        return;
      }

      const job = await resp.json();

      if (job.status === 'completed') {
        showResults(job.result || {});
        done();
      } else if (job.status === 'failed') {
        showErrors([job.error_message || 'Analysis failed']);
        done();
      } else {
        setTimeout(() => pollJob(jobId), POLL_INTERVAL_MS);
      }
    } catch (e) {
      showErrors([e.message || 'Network error']);
      done();
    }
  }

  function done() {
    spinner.classList.add('hidden');
    btn.disabled = false;
  }

  function showErrors(errors) {
    errorsEl.innerHTML = '<ul>' + errors.map(e => '<li>' + escapeHtml(e) + '</li>').join('') + '</ul>';
    errorsEl.classList.remove('hidden');
  }

  function showResults(data) {
    const ecoText = [data.eco_code, data.eco_name].filter(Boolean).join(' — ') || '—';
    document.getElementById('resEco').textContent = ecoText;
    document.getElementById('resMoves').textContent = data.total_moves || 0;
    document.getElementById('resBlunders').textContent = data.blunders || 0;
    document.getElementById('resMistakes').textContent = data.mistakes || 0;
    document.getElementById('resInaccuracies').textContent = data.inaccuracies || 0;
    results.classList.remove('hidden');
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }
})();
