/**
 * Async theme sync — fetches theme from server and updates localStorage cache.
 * Runs at the bottom of every page after initial render.
 */
(function() {
  fetch('/api/settings/theme')
    .then(r => r.json())
    .then(theme => {
      localStorage.setItem('theme', JSON.stringify(theme));
      if (window.applyTheme) {
        window.applyTheme(theme);
      }
    })
    .catch(() => {});
})();
