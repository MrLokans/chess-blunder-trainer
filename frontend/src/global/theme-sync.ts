interface ThemeColors {
  [key: string]: string | undefined;
}

fetch('/api/settings/theme')
  .then(r => r.json() as Promise<ThemeColors>)
  .then(theme => {
    localStorage.setItem('theme', JSON.stringify(theme));
    if (window.applyTheme) {
      window.applyTheme(theme);
    }
  })
  .catch(() => { /* ignore */ });
