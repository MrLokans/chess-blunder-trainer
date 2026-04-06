import { client } from '../shared/api';
import { debounce } from '../shared/debounce';

localStorage.clear();

const form = document.getElementById('setupForm') as HTMLFormElement | null;
const errorAlert = document.getElementById('errorAlert');
const submitBtn = document.getElementById('submitBtn') as HTMLButtonElement | null;
const lichessInput = document.getElementById('lichess') as HTMLInputElement | null;
const chesscomInput = document.getElementById('chesscom') as HTMLInputElement | null;
const lichessStatus = document.getElementById('lichessStatus');
const chesscomStatus = document.getElementById('chesscomStatus');
const progressSection = document.getElementById('setupProgress');
const progressMessage = document.getElementById('setupProgressMessage');

const validationState: Record<string, boolean | null> = { lichess: null, chesscom: null };

function showError(message: string): void {
  if (errorAlert) {
    errorAlert.textContent = message;
    errorAlert.classList.add('visible');
  }
}

function hideError(): void {
  errorAlert?.classList.remove('visible');
}

function setFieldStatus(statusEl: HTMLElement | null, state: string | null): void {
  if (!statusEl) return;
  statusEl.className = 'field-validation';
  statusEl.textContent = '';
  if (state === 'checking') {
    statusEl.classList.add('checking');
    statusEl.textContent = t('setup.validating');
  } else if (state === 'valid') {
    statusEl.classList.add('valid');
    statusEl.textContent = t('setup.username_valid');
  } else if (state === 'invalid') {
    statusEl.classList.add('invalid');
    statusEl.textContent = t('setup.username_invalid');
  }
}

async function validateField(platform: string, input: HTMLInputElement, statusEl: HTMLElement | null): Promise<void> {
  const username = input.value.trim();
  if (!username) {
    validationState[platform] = null;
    if (statusEl) {
      statusEl.className = 'field-validation';
      statusEl.textContent = '';
    }
    return;
  }

  setFieldStatus(statusEl, 'checking');
  try {
    const result = await client.setup.validateUsername(platform, username) as { valid: boolean };
    if (input.value.trim() !== username) return;
    validationState[platform] = result.valid;
    setFieldStatus(statusEl, result.valid ? 'valid' : 'invalid');
  } catch {
    if (input.value.trim() !== username) return;
    validationState[platform] = null;
    if (statusEl) {
      statusEl.className = 'field-validation';
      statusEl.textContent = '';
    }
  }
}

const debouncedValidateLichess = debounce(
  () => { if (lichessInput) validateField('lichess', lichessInput, lichessStatus); },
  500,
);
const debouncedValidateChesscom = debounce(
  () => { if (chesscomInput) validateField('chesscom', chesscomInput, chesscomStatus); },
  500,
);

lichessInput?.addEventListener('input', () => {
  validationState.lichess = null;
  setFieldStatus(lichessStatus, lichessInput!.value.trim() ? 'checking' : null);
  debouncedValidateLichess();
});

chesscomInput?.addEventListener('input', () => {
  validationState.chesscom = null;
  setFieldStatus(chesscomStatus, chesscomInput!.value.trim() ? 'checking' : null);
  debouncedValidateChesscom();
});

async function validateAllFields(): Promise<void> {
  const promises: Promise<void>[] = [];
  if (lichessInput?.value.trim()) {
    promises.push(validateField('lichess', lichessInput, lichessStatus));
  }
  if (chesscomInput?.value.trim()) {
    promises.push(validateField('chesscom', chesscomInput, chesscomStatus));
  }
  await Promise.all(promises);
}

function getValidationErrors(): string[] {
  const errors: string[] = [];
  const lichess = lichessInput?.value.trim() ?? '';
  const chesscom = chesscomInput?.value.trim() ?? '';

  if (lichess && validationState.lichess === false) {
    errors.push(t('setup.lichess_not_found', { username: lichess }));
  }
  if (chesscom && validationState.chesscom === false) {
    errors.push(t('setup.chesscom_not_found', { username: chesscom }));
  }
  return errors;
}

const SETUP_WAIT_MS = 15000;
const POLL_INTERVAL_MS = 2000;

function showProgress(message: string): void {
  progressSection?.classList.remove('hidden');
  if (progressMessage) progressMessage.textContent = message;
  form?.classList.add('hidden');
}

async function waitForAnalysis(jobIds: string[]): Promise<void> {
  const deadline = Date.now() + SETUP_WAIT_MS;

  showProgress(t('setup.importing'));

  while (Date.now() < deadline) {
    await new Promise<void>(r => setTimeout(r, POLL_INTERVAL_MS));

    try {
      const statusResp = await client.analysis.status() as { status: string };
      if (statusResp.status === 'completed') {
        return;
      }

      const jobs = await Promise.all(
        jobIds.map(id => client.jobs.getImportStatus(id).catch(() => null) as Promise<{ status: string } | null>),
      );
      const allDone = jobs.every(j => j && (j.status === 'completed' || j.status === 'failed'));
      if (allDone) {
        showProgress(t('setup.analyzing'));
      }
    } catch {
      // continue polling
    }
  }
}

form?.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideError();

  const lichess = lichessInput?.value.trim() ?? '';
  const chesscom = chesscomInput?.value.trim() ?? '';

  if (!lichess && !chesscom) {
    showError(t('setup.username_error'));
    return;
  }

  if (submitBtn) {
    submitBtn.disabled = true;
    submitBtn.textContent = t('setup.submitting');
  }

  await validateAllFields();

  const errors = getValidationErrors();
  if (errors.length > 0) {
    showError(errors.join(' '));
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('setup.submit');
    }
    return;
  }

  try {
    const result = await client.setup.complete({ lichess, chesscom }) as { import_job_ids?: string[] };
    const jobIds = result.import_job_ids || [];

    if (jobIds.length > 0) {
      await waitForAnalysis(jobIds);
    }

    trackEvent('Setup Completed', {
      has_lichess: lichess ? 'yes' : 'no',
      has_chesscom: chesscom ? 'yes' : 'no',
    });
    window.location.href = '/';
  } catch (err) {
    showError((err as Error).message || t('setup.failed'));
    if (submitBtn) {
      submitBtn.disabled = false;
      submitBtn.textContent = t('setup.submit');
    }
    form?.classList.remove('hidden');
    progressSection?.classList.add('hidden');
  }
});
