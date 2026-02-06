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
    showError('Please provide at least one username (Lichess or Chess.com)');
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = 'Setting up...';

  try {
    await client.setup.complete({ lichess, chesscom });
    window.location.href = '/';
  } catch (err) {
    showError(err.message || 'Setup failed. Please try again.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Get Started';
    console.error(err);
  }
});
