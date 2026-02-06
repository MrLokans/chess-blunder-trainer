import { client } from './api.js';

const form = document.getElementById('setupForm');
const errorAlert = document.getElementById('errorAlert');
const submitBtn = document.getElementById('submitBtn');
const lichessInput = document.getElementById('lichess');
const chesscomInput = document.getElementById('chesscom');

function showError(message) {
  errorAlert.textContent = message;
  errorAlert.classList.add('visible');
}

function hideError() {
  errorAlert.classList.remove('visible');
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

  try {
    await client.setup.complete({ lichess, chesscom });
    window.location.href = '/';
  } catch (err) {
    showError(err.message || t('setup.failed'));
    submitBtn.disabled = false;
    submitBtn.textContent = t('setup.submit');
    console.error(err);
  }
});
