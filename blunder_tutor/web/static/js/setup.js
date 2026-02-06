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
    const response = await fetch('/api/setup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lichess, chesscom })
    });

    const data = await response.json();

    if (response.ok) {
      window.location.href = '/';
    } else {
      showError(data.error || 'Setup failed. Please try again.');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Get Started';
    }
  } catch (err) {
    showError('Network error. Please try again.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Get Started';
    console.error(err);
  }
});
