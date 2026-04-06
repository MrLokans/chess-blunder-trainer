interface ThemeColors {
  [key: string]: string | undefined;
}

fetch('/api/settings/theme')
  .then(r => r.json() as Promise<ThemeColors>)
  .then(theme => {
    localStorage.setItem('theme', JSON.stringify(theme));
    const apply = (window as unknown as Record<string, unknown>).applyTheme;
    if (typeof apply === 'function') {
      (apply as (t: ThemeColors) => void)(theme);
    }
  })
  .catch(() => { /* ignore */ });
