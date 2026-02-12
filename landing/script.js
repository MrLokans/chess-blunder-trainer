document.addEventListener('DOMContentLoaded', () => {
  const copyBtn = document.querySelector('.copy-btn');
  if (copyBtn) {
    copyBtn.addEventListener('click', () => {
      const code = 'docker run -p 8000:8000 -v $(pwd)/data:/app/data ghcr.io/mrlokans/blunder-tutor:latest';
      navigator.clipboard.writeText(code).then(() => {
        const original = copyBtn.textContent;
        copyBtn.textContent = 'Copied!';
        setTimeout(() => { copyBtn.textContent = original; }, 2000);
      });
    });
  }

  const hamburger = document.querySelector('.nav__hamburger');
  const nav = document.querySelector('.nav');
  if (hamburger) {
    hamburger.addEventListener('click', () => {
      nav.classList.toggle('nav--open');
    });

    document.querySelectorAll('.nav__links a').forEach(link => {
      link.addEventListener('click', () => {
        nav.classList.remove('nav--open');
      });
    });
  }
});
