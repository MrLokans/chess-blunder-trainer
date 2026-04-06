import { setupColorInput } from '../shared/color-input';
import { client } from '../shared/api';

interface PieceSet {
  id: string;
  name: string;
}

interface BoardColorPreset {
  id: string;
  name: string;
  light: string;
  dark: string;
}

let pieceSets: PieceSet[] = [];
let boardColorPresets: BoardColorPreset[] = [];
let currentPieceSet = 'gioco';
let currentBoardLight = '#E0E0E0';
let currentBoardDark = '#A0A0A0';
let activeBoardColorPreset: string | null = null;

const boardPreview = document.getElementById('boardPreview');
const pieceSetGrid = document.getElementById('pieceSetGrid');
const boardColorPresetsEl = document.getElementById('boardColorPresets');
const boardLightColor = document.getElementById('boardLightColor') as HTMLInputElement | null;
const boardLightHex = document.getElementById('boardLightHex') as HTMLInputElement | null;
const boardDarkColor = document.getElementById('boardDarkColor') as HTMLInputElement | null;
const boardDarkHex = document.getElementById('boardDarkHex') as HTMLInputElement | null;

const previewPieces: (string | null)[][] = [
  ['bR', null, 'bB', 'bK'],
  [null, 'bP', null, 'bP'],
  ['wP', null, 'wN', null],
  ['wR', null, 'wB', 'wK'],
];

function getPieceImageUrl(piece: string | null): string | null {
  if (!piece) return null;
  const format = 'svg';
  return `/static/pieces/${currentPieceSet}/${piece}.${format}`;
}

function renderBoardPreview(): void {
  if (!boardPreview) return;
  const root = document.documentElement;
  root.style.setProperty('--preview-board-light', currentBoardLight);
  root.style.setProperty('--preview-board-dark', currentBoardDark);

  let html = '';
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 4; col++) {
      const isLight = (row + col) % 2 === 0;
      const piece = previewPieces[row]![col]!;
      const pieceImg = piece ? `<img src="${getPieceImageUrl(piece)}" alt="${piece}">` : '';
      html += `<div class="square ${isLight ? 'light' : 'dark'}">${pieceImg}</div>`;
    }
  }
  boardPreview.innerHTML = html;
}

function renderPieceSetGrid(): void {
  if (!pieceSetGrid) return;
  pieceSetGrid.innerHTML = pieceSets.map(ps => `
    <div class="piece-set-card ${currentPieceSet === ps.id ? 'active' : ''}" data-piece-set="${ps.id}">
      ${ps.name}
    </div>
  `).join('');

  pieceSetGrid.querySelectorAll<HTMLElement>('.piece-set-card').forEach(card => {
    card.addEventListener('click', () => {
      currentPieceSet = card.dataset.pieceSet ?? currentPieceSet;
      renderPieceSetGrid();
      renderBoardPreview();
    });
  });
}

function renderBoardColorPresets(): void {
  if (!boardColorPresetsEl) return;
  boardColorPresetsEl.innerHTML = boardColorPresets.map(preset => `
    <div class="board-color-preset ${activeBoardColorPreset === preset.id ? 'active' : ''}"
         data-preset-id="${preset.id}"
         data-light="${preset.light}"
         data-dark="${preset.dark}"
         title="${preset.name}">
      <div class="light" style="background: ${preset.light};"></div>
      <div class="light-alt" style="background: ${preset.dark};"></div>
      <div class="dark-alt" style="background: ${preset.light};"></div>
      <div class="dark" style="background: ${preset.dark};"></div>
    </div>
  `).join('');

  boardColorPresetsEl.querySelectorAll<HTMLElement>('.board-color-preset').forEach(preset => {
    preset.addEventListener('click', () => {
      currentBoardLight = preset.dataset.light ?? currentBoardLight;
      currentBoardDark = preset.dataset.dark ?? currentBoardDark;
      activeBoardColorPreset = preset.dataset.presetId ?? null;

      if (boardLightColor) boardLightColor.value = currentBoardLight;
      if (boardLightHex) boardLightHex.value = currentBoardLight.toUpperCase();
      if (boardDarkColor) boardDarkColor.value = currentBoardDark;
      if (boardDarkHex) boardDarkHex.value = currentBoardDark.toUpperCase();

      renderBoardColorPresets();
      renderBoardPreview();
    });
  });
}

function clearActiveBoardColorPreset(): void {
  activeBoardColorPreset = null;
  boardColorPresetsEl?.querySelectorAll('.board-color-preset').forEach(el => {
    el.classList.remove('active');
  });
}

function checkIfMatchesBoardColorPreset(): void {
  for (const preset of boardColorPresets) {
    if (preset.light.toLowerCase() === currentBoardLight.toLowerCase() &&
        preset.dark.toLowerCase() === currentBoardDark.toLowerCase()) {
      activeBoardColorPreset = preset.id;
      return;
    }
  }
  activeBoardColorPreset = null;
}

if (boardLightColor && boardLightHex) {
  setupColorInput(boardLightColor, boardLightHex, (val) => {
    currentBoardLight = val;
    clearActiveBoardColorPreset();
    renderBoardPreview();
  });
}

if (boardDarkColor && boardDarkHex) {
  setupColorInput(boardDarkColor, boardDarkHex, (val) => {
    currentBoardDark = val;
    clearActiveBoardColorPreset();
    renderBoardPreview();
  });
}

document.getElementById('resetBoardBtn')?.addEventListener('click', () => {
  currentPieceSet = 'gioco';
  currentBoardLight = '#E0E0E0';
  currentBoardDark = '#A0A0A0';

  if (boardLightColor) boardLightColor.value = currentBoardLight;
  if (boardLightHex) boardLightHex.value = currentBoardLight.toUpperCase();
  if (boardDarkColor) boardDarkColor.value = currentBoardDark;
  if (boardDarkHex) boardDarkHex.value = currentBoardDark.toUpperCase();

  checkIfMatchesBoardColorPreset();
  renderPieceSetGrid();
  renderBoardColorPresets();
  renderBoardPreview();
});

export async function initBoardEditor(): Promise<void> {
  try {
    const pieceSetsData = await client.settings.getPieceSets() as { piece_sets: PieceSet[] };
    pieceSets = pieceSetsData.piece_sets;

    const colorPresetsData = await client.settings.getBoardColorPresets() as { presets: BoardColorPreset[] };
    boardColorPresets = colorPresetsData.presets;

    const settings = await client.settings.getBoard() as { piece_set: string; board_light: string; board_dark: string };
    currentPieceSet = settings.piece_set;
    currentBoardLight = settings.board_light;
    currentBoardDark = settings.board_dark;

    if (boardLightColor) boardLightColor.value = currentBoardLight;
    if (boardLightHex) boardLightHex.value = currentBoardLight.toUpperCase();
    if (boardDarkColor) boardDarkColor.value = currentBoardDark;
    if (boardDarkHex) boardDarkHex.value = currentBoardDark.toUpperCase();

    checkIfMatchesBoardColorPreset();
    renderPieceSetGrid();
    renderBoardColorPresets();
    renderBoardPreview();
  } catch (err) {
    console.error('Failed to load board settings:', err);
  }
}

export async function saveBoardSettings(): Promise<void> {
  try {
    await client.settings.saveBoard({
      piece_set: currentPieceSet,
      board_light: currentBoardLight,
      board_dark: currentBoardDark,
    });
  } catch (err) {
    console.error('Failed to save board settings:', err);
  }
}
