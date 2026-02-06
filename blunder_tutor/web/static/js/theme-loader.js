/**
 * Theme loader — must run synchronously in <head> to avoid FOUC.
 * Also exposes applyTheme/adjustColor for use by settings and the async sync.
 */
(function() {
  function adjustColor(hex, lightness, saturation) {
    const r = parseInt(hex.slice(1, 3), 16) / 255;
    const g = parseInt(hex.slice(3, 5), 16) / 255;
    const b = parseInt(hex.slice(5, 7), 16) / 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, l = (max + min) / 2;

    if (max === min) {
      h = s = 0;
    } else {
      const d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      switch (max) {
        case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
        case g: h = ((b - r) / d + 2) / 6; break;
        case b: h = ((r - g) / d + 4) / 6; break;
      }
    }

    if (typeof lightness === 'number') l = lightness / 100;
    if (typeof saturation === 'number') s = saturation;

    function hue2rgb(p, q, t) {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    }

    let r2, g2, b2;
    if (s === 0) {
      r2 = g2 = b2 = l;
    } else {
      const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
      const p = 2 * l - q;
      r2 = hue2rgb(p, q, h + 1/3);
      g2 = hue2rgb(p, q, h);
      b2 = hue2rgb(p, q, h - 1/3);
    }

    const toHex = x => Math.round(x * 255).toString(16).padStart(2, '0');
    return `#${toHex(r2)}${toHex(g2)}${toHex(b2)}`;
  }

  function applyTheme(theme) {
    const root = document.documentElement;

    if (theme.primary) {
      root.style.setProperty('--color-primary', theme.primary);
      root.style.setProperty('--color-primary-hover', adjustColor(theme.primary, -15));
      root.style.setProperty('--color-primary-muted', adjustColor(theme.primary, 20));
    }
    if (theme.success) {
      root.style.setProperty('--color-success', theme.success);
      root.style.setProperty('--color-success-bg', adjustColor(theme.success, 85, 0.15));
      root.style.setProperty('--color-success-border', adjustColor(theme.success, 50, 0.4));
    }
    if (theme.error) {
      root.style.setProperty('--color-error', theme.error);
      root.style.setProperty('--color-error-bg', adjustColor(theme.error, 85, 0.15));
      root.style.setProperty('--color-error-border', adjustColor(theme.error, 50, 0.4));
    }
    if (theme.warning) {
      root.style.setProperty('--color-warning', theme.warning);
      root.style.setProperty('--color-warning-bg', adjustColor(theme.warning, 85, 0.15));
      root.style.setProperty('--color-warning-border', adjustColor(theme.warning, 50, 0.4));
    }

    if (theme.phase_opening) root.style.setProperty('--color-phase-opening', theme.phase_opening);
    if (theme.phase_middlegame) root.style.setProperty('--color-phase-middlegame', theme.phase_middlegame);
    if (theme.phase_endgame) root.style.setProperty('--color-phase-endgame', theme.phase_endgame);

    if (theme.heatmap_empty) root.style.setProperty('--heatmap-empty', theme.heatmap_empty);
    if (theme.heatmap_l1) root.style.setProperty('--heatmap-l1', theme.heatmap_l1);
    if (theme.heatmap_l2) root.style.setProperty('--heatmap-l2', theme.heatmap_l2);
    if (theme.heatmap_l3) root.style.setProperty('--heatmap-l3', theme.heatmap_l3);
    if (theme.heatmap_l4) root.style.setProperty('--heatmap-l4', theme.heatmap_l4);

    if (theme.bg) root.style.setProperty('--bg', theme.bg);
    if (theme.bg_card) root.style.setProperty('--bg-elevated', theme.bg_card);
    if (theme.text) root.style.setProperty('--text', theme.text);
    if (theme.text_muted) root.style.setProperty('--text-muted', theme.text_muted);
  }

  // Apply cached theme immediately to prevent FOUC
  const cached = localStorage.getItem('theme');
  if (cached) {
    try { applyTheme(JSON.parse(cached)); } catch (e) {}
  }

  window.adjustColor = adjustColor;
  window.applyTheme = applyTheme;
})();
