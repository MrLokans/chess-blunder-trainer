import { client } from './api.js';
import { debounce } from './debounce.js';

localStorage.clear();

const form = document.getElementById('setupForm');
const errorAlert = document.getElementById('errorAlert');
const submitBtn = document.getElementById('submitBtn');
const lichessInput = document.getElementById('lichess');
const chesscomInput = document.getElementById('chesscom');
const lichessStatus = document.getElementById('lichessStatus');
const chesscomStatus = document.getElementById('chesscomStatus');
const progressSection = document.getElementById('setupProgress');
const progressMessage = document.getElementById('setupProgressMessage');

const validationState = { lichess: null, chesscom: null };

function showError(message) {
  errorAlert.textContent = message;
  errorAlert.classList.add('visible');
}

function hideError() {
  errorAlert.classList.remove('visible');
}

function setFieldStatus(statusEl, state) {
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

async function validateField(platform, input, statusEl) {
  const username = input.value.trim();
  if (!username) {
    validationState[platform] = null;
    statusEl.className = 'field-validation';
    statusEl.textContent = '';
    return;
  }

  setFieldStatus(statusEl, 'checking');
  try {
    const result = await client.setup.validateUsername(platform, username);
    if (input.value.trim() !== username) return;
    validationState[platform] = result.valid;
    setFieldStatus(statusEl, result.valid ? 'valid' : 'invalid');
  } catch {
    if (input.value.trim() !== username) return;
    validationState[platform] = null;
    statusEl.className = 'field-validation';
    statusEl.textContent = '';
  }
}

const debouncedValidateLichess = debounce(() => validateField('lichess', lichessInput, lichessStatus), 500);
const debouncedValidateChesscom = debounce(() => validateField('chesscom', chesscomInput, chesscomStatus), 500);

lichessInput.addEventListener('input', () => {
  validationState.lichess = null;
  setFieldStatus(lichessStatus, lichessInput.value.trim() ? 'checking' : null);
  debouncedValidateLichess();
});

chesscomInput.addEventListener('input', () => {
  validationState.chesscom = null;
  setFieldStatus(chesscomStatus, chesscomInput.value.trim() ? 'checking' : null);
  debouncedValidateChesscom();
});

async function validateAllFields() {
  const promises = [];
  const lichess = lichessInput.value.trim();
  const chesscom = chesscomInput.value.trim();

  if (lichess) {
    promises.push(validateField('lichess', lichessInput, lichessStatus));
  }
  if (chesscom) {
    promises.push(validateField('chesscom', chesscomInput, chesscomStatus));
  }
  await Promise.all(promises);
}

function getValidationErrors() {
  const errors = [];
  const lichess = lichessInput.value.trim();
  const chesscom = chesscomInput.value.trim();

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

function showProgress(message) {
  progressSection.style.display = 'block';
  progressMessage.textContent = message;
  form.style.display = 'none';
}

async function waitForAnalysis(jobIds) {
  const deadline = Date.now() + SETUP_WAIT_MS;

  showProgress(t('setup.importing'));

  while (Date.now() < deadline) {
    await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));

    try {
      const statusResp = await client.analysis.status();
      if (statusResp.status === 'completed') {
        return;
      }

      const jobs = await Promise.all(jobIds.map(id => client.jobs.getImportStatus(id).catch(() => null)));
      const allDone = jobs.every(j => j && (j.status === 'completed' || j.status === 'failed'));
      if (allDone) {
        showProgress(t('setup.analyzing'));
      }
    } catch {
      // continue polling
    }
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideError();

  const lichess = lichessInput.value.trim();
  const chesscom = chesscomInput.value.trim();

  if (!lichess && !chesscom) {
    showError(t('setup.username_error'));
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = t('setup.submitting');

  await validateAllFields();

  const errors = getValidationErrors();
  if (errors.length > 0) {
    showError(errors.join(' '));
    submitBtn.disabled = false;
    submitBtn.textContent = t('setup.submit');
    return;
  }

  try {
    const result = await client.setup.complete({ lichess, chesscom });
    const jobIds = result.import_job_ids || [];

    if (jobIds.length > 0) {
      await waitForAnalysis(jobIds);
    }

    window.location.href = '/';
  } catch (err) {
    showError(err.message || t('setup.failed'));
    submitBtn.disabled = false;
    submitBtn.textContent = t('setup.submit');
    form.style.display = 'block';
    progressSection.style.display = 'none';
  }
});
