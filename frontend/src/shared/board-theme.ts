export function applyBoardBackground(light: string, dark: string): void {
  const id = 'cg-board-bg';
  let style = document.getElementById(id) as HTMLStyleElement | null;
  if (!style) {
    style = document.createElement('style');
    style.id = id;
    document.head.appendChild(style);
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 8 8" shape-rendering="crispEdges">` +
    `<rect width="8" height="8" fill="${light}"/>` +
    Array.from({ length: 64 }, (_, i) => {
      const x = i % 8, y = Math.floor(i / 8);
      return (x + y) % 2 === 1 ? `<rect x="${x}" y="${y}" width="1" height="1" fill="${dark}"/>` : '';
    }).join('') +
    `</svg>`;
  const encoded = 'data:image/svg+xml;base64,' + btoa(svg);
  style.textContent = `cg-board { background-image: url("${encoded}") !important; }`;
  document.documentElement.style.setProperty('--board-light', light);
  document.documentElement.style.setProperty('--board-dark', dark);
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
      const file = `${colorMap[color]}${pieceMap[role]}`;
      const url = `/static/pieces/${pieceSet}/${file}.svg`;
      css += `.cg-wrap piece.${role}.${color} { background-image: url(${url}); }\n`;
      css += `.cg-wrap piece.ghost.${role}.${color} { background-image: url(${url}); }\n`;
    }
  }
  style.textContent = css;
}
