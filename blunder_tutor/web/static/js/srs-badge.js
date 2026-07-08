// Fills the nav "reviews due" badge on every page. Kept as a plain
// static script (like theme-loader.js) because the nav is server-rendered
// and shared across pages, while Vite entries are per-page.
(function () {
  const badge = document.getElementById('srsNavBadge');
  const features = window.__features || {};
  if (!badge || !features['trainer.srs']) return;

  fetch('/api/srs/status')
    .then((resp) => (resp.ok ? resp.json() : null))
    .then((status) => {
      if (status && status.due > 0) {
        badge.textContent = String(status.due);
        badge.hidden = false;
      }
    })
    .catch(() => {});
})();
