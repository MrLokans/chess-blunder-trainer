export interface BoardColors {
  light: string;
  dark: string;
}

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

export function applyBoardTheme(light: string | null, dark: string | null): void {
  const root = document.documentElement;
  if (light && dark) {
    root.style.setProperty('--board-light', light);
    root.style.setProperty('--board-dark', dark);
  } else {
    root.style.removeProperty('--board-light');
    root.style.removeProperty('--board-dark');
  }
  document.getElementById('cg-board-bg')?.remove();
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
