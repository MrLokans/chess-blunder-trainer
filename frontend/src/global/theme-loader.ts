export interface ThemeColors {
  primary?: string;
  success?: string;
  error?: string;
  warning?: string;
  phase_opening?: string;
  phase_middlegame?: string;
  phase_endgame?: string;
  heatmap_empty?: string;
  heatmap_l1?: string;
  heatmap_l2?: string;
  heatmap_l3?: string;
  heatmap_l4?: string;
  bg?: string;
  bg_card?: string;
  text?: string;
  text_muted?: string;
}

export function adjustColor(hex: string, lightness: number | null, saturation?: number): string {
  const r = parseInt(hex.slice(1, 3), 16) / 255;
  const g = parseInt(hex.slice(3, 5), 16) / 255;
  const b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h = 0, s: number, l = (max + min) / 2;

  if (max === min) {
    h = 0; s = 0;
  } else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
      case g: h = ((b - r) / d + 2) / 6; break;
      case b: h = ((r - g) / d + 4) / 6; break;
    }
  }

  if (typeof lightness === 'number') {
    l = Math.min(1, Math.max(0, lightness < 0 ? l + lightness / 100 : lightness / 100));
  }
  if (typeof saturation === 'number') s = Math.min(1, Math.max(0, saturation));

  function hue2rgb(p: number, q: number, t: number): number {
    if (t < 0) t += 1;
    if (t > 1) t -= 1;
    if (t < 1 / 6) return p + (q - p) * 6 * t;
    if (t < 1 / 2) return q;
    if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
    return p;
  }

  let r2: number, g2: number, b2: number;
  if (s === 0) {
    r2 = g2 = b2 = l;
  } else {
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r2 = hue2rgb(p, q, h + 1 / 3);
    g2 = hue2rgb(p, q, h);
    b2 = hue2rgb(p, q, h - 1 / 3);
  }

  const toHex = (x: number): string => Math.round(x * 255).toString(16).padStart(2, '0');
  return `#${toHex(r2)}${toHex(g2)}${toHex(b2)}`;
}

const USER_PROPERTIES: Record<keyof ThemeColors, string> = {
  primary: '--user-accent', success: '--user-success', error: '--user-error',
  warning: '--user-warning', phase_opening: '--user-phase-opening',
  phase_middlegame: '--user-phase-middlegame', phase_endgame: '--user-phase-endgame',
  heatmap_empty: '--user-heatmap-empty', heatmap_l1: '--user-heatmap-l1',
  heatmap_l2: '--user-heatmap-l2', heatmap_l3: '--user-heatmap-l3',
  heatmap_l4: '--user-heatmap-l4', bg: '--user-surface',
  bg_card: '--user-surface-raised', text: '--user-text', text_muted: '--user-text-muted',
};

export function removeTheme(): void {
  const root = document.documentElement;
  for (const property of Object.values(USER_PROPERTIES)) {
    root.style.removeProperty(property);
  }
  for (const property of [
    '--user-accent-hover', '--user-success-bg', '--user-success-border',
    '--user-error-bg', '--user-error-border', '--user-warning-bg', '--user-warning-border',
  ]) {
    root.style.removeProperty(property);
  }
}

export function applyTheme(theme: ThemeColors): void {
  const root = document.documentElement;
  const derived = {
    '--user-accent-hover': theme.primary && adjustColor(theme.primary, -15),
    '--user-success-bg': theme.success && adjustColor(theme.success, 85, 0.15),
    '--user-success-border': theme.success && adjustColor(theme.success, 50, 0.4),
    '--user-error-bg': theme.error && adjustColor(theme.error, 85, 0.15),
    '--user-error-border': theme.error && adjustColor(theme.error, 50, 0.4),
    '--user-warning-bg': theme.warning && adjustColor(theme.warning, 85, 0.15),
    '--user-warning-border': theme.warning && adjustColor(theme.warning, 50, 0.4),
  };

  removeTheme();
  for (const [key, property] of Object.entries(USER_PROPERTIES) as Array<[keyof ThemeColors, string]>) {
    const value = theme[key];
    if (value) root.style.setProperty(property, value);
  }
  for (const [property, value] of Object.entries(derived)) {
    if (value) root.style.setProperty(property, value);
  }
}

const HEX_COLOR = /^#[0-9a-f]{6}$/i;

function isTheme(value: unknown): value is ThemeColors {
  if (!value || typeof value !== 'object') return false;
  return Object.keys(USER_PROPERTIES).every(key => {
    const color = (value as Record<string, unknown>)[key];
    return color === undefined || (typeof color === 'string' && HEX_COLOR.test(color));
  });
}

function syncTheme(): void {
  fetch('/api/settings/theme')
    .then(response => response.json() as Promise<ThemeColors>)
    .then(theme => {
      localStorage.setItem('theme', JSON.stringify(theme));
      applyTheme(theme);
    })
    .catch(() => {});
}

(function () {
  const cached = localStorage.getItem('theme');
  if (cached) {
    try {
      const theme: unknown = JSON.parse(cached);
      if (isTheme(theme)) applyTheme(theme);
      else localStorage.removeItem('theme');
    } catch {
      localStorage.removeItem('theme');
    }
  }

  window.adjustColor = adjustColor;
  window.applyTheme = applyTheme;
  window.removeTheme = removeTheme;
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', syncTheme, { once: true });
  } else {
    syncTheme();
  }
})();
