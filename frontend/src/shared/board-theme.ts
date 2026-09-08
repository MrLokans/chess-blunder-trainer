export function buildBoardSvgDataUrl(light: string, dark: string): string {
  const squares = Array.from({ length: 64 }, (_, i) => {
    const x = i % 8, y = Math.floor(i / 8);
    return (x + y) % 2 === 1 ? `<rect x="${String(x)}" y="${String(y)}" width="1" height="1" fill="${dark}"/>` : '';
  }).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">` +
    `<rect width="8" height="8" fill="${light}"/>${squares}</svg>`;
  return 'data:image/svg+xml;base64,' + btoa(svg);
}

export interface BoardColors {
  light: string;
  dark: string;
}

/**
 * Effective board square colours: an explicit user choice written as an inline
 * custom property if there is one, otherwise the mode-aware default declared in
 * tokens.css.
 */
function resolveBoardColor(property: string): string {
  const probe = document.createElement('span');
  probe.style.color = `var(${property})`;
  document.body.appendChild(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  if (color.startsWith('var(')) {
    return getComputedStyle(document.documentElement).getPropertyValue(property).trim();
  }

  const channels = color.match(/\d+/g);
  if (!channels) return color;
  const hex = channels.slice(0, 3)
    .map(channel => Number(channel).toString(16).padStart(2, '0'))
    .join('');
  return `#${hex.toUpperCase()}`;
}

export function readBoardColors(): BoardColors {
  return {
    light: resolveBoardColor('--board-light'),
    dark: resolveBoardColor('--board-dark'),
  };
}

export function paintBoardBackground(): void {
  const id = 'cg-board-bg';
  let style = document.getElementById(id) as HTMLStyleElement | null;
  if (!style) {
    style = document.createElement('style');
    style.id = id;
    document.head.appendChild(style);
  }
  const { light, dark } = readBoardColors();
  const encoded = buildBoardSvgDataUrl(light, dark);
  style.textContent = `cg-board { background-image: url("${encoded}") !important; }`;
}

// The board is painted as an SVG data URL, so a CSS-only default cannot repaint
// it when the theme flips. Track whether we are on the token default and, if so,
// repaint on themechange.
let followingTokenDefault = false;
let themeListenerAttached = false;

function attachThemeListener(): void {
  if (themeListenerAttached) return;
  window.addEventListener('themechange', () => {
    if (followingTokenDefault) paintBoardBackground();
  });
  themeListenerAttached = true;
}

/**
 * Apply the user's stored board colours, or fall back to the mode-aware default
 * when they have never chosen any (`null`). Explicit colours win in both modes.
 */
export function applyBoardTheme(light: string | null, dark: string | null): void {
  const root = document.documentElement;
  if (light && dark) {
    followingTokenDefault = false;
    root.style.setProperty('--board-light', light);
    root.style.setProperty('--board-dark', dark);
  } else {
    followingTokenDefault = true;
    root.style.removeProperty('--board-light');
    root.style.removeProperty('--board-dark');
  }
  paintBoardBackground();
  attachThemeListener();
}

export function applyPieceSet(pieceSet: string): void {
  const id = 'cg-piece-set';
  let style = document.getElementById(id) as HTMLStyleElement | null;
  if (!style) {
    style = document.createElement('style');
    style.id = id;
    document.head.appendChild(style);
  }
  const pieces = ['pawn', 'rook', 'knight', 'bishop', 'queen', 'king'];
  const colorMap: Record<string, string> = { white: 'w', black: 'b' };
  const pieceMap: Record<string, string> = { pawn: 'P', rook: 'R', knight: 'N', bishop: 'B', queen: 'Q', king: 'K' };
  let css = '';
  for (const color of ['white', 'black']) {
    for (const role of pieces) {
      const file = `${colorMap[color] ?? ''}${pieceMap[role] ?? ''}`;
      const url = `/static/pieces/${pieceSet}/${file}.svg`;
      css += `.cg-wrap piece.${role}.${color} { background-image: url(${url}); }\n`;
      css += `.cg-wrap piece.ghost.${role}.${color} { background-image: url(${url}); }\n`;
    }
  }
  style.textContent = css;
}
