import { setupColorInput } from '../color-input.js';
import { client } from '../api.js';

let pieceSets = [];
let boardColorPresets = [];
let currentPieceSet = 'wikipedia';
let currentBoardLight = '#f0d9b5';
let currentBoardDark = '#b58863';
let activeBoardColorPreset = null;

const boardPreview = document.getElementById('boardPreview');
const pieceSetGrid = document.getElementById('pieceSetGrid');
const boardColorPresetsEl = document.getElementById('boardColorPresets');
const boardLightColor = document.getElementById('boardLightColor');
const boardLightHex = document.getElementById('boardLightHex');
const boardDarkColor = document.getElementById('boardDarkColor');
const boardDarkHex = document.getElementById('boardDarkHex');

const previewPieces = [
  ['bR', null, 'bB', 'bK'],
  [null, 'bP', null, 'bP'],
  ['wP', null, 'wN', null],
  ['wR', null, 'wB', 'wK']
];

function getPieceImageUrl(piece) {
  if (!piece) return null;
  const format = currentPieceSet === 'wikipedia' ? 'png' : 'svg';
  return `/static/pieces/${currentPieceSet}/${piece}.${format}`;
}

function renderBoardPreview() {
  const root = document.documentElement;
  root.style.setProperty('--preview-board-light', currentBoardLight);
  root.style.setProperty('--preview-board-dark', currentBoardDark);

  let html = '';
  for (let row = 0; row < 4; row++) {
    for (let col = 0; col < 4; col++) {
      const isLight = (row + col) % 2 === 0;
      const piece = previewPieces[row][col];
      const pieceImg = piece ? `<img src="${getPieceImageUrl(piece)}" alt="${piece}">` : '';
      html += `<div class="square ${isLight ? 'light' : 'dark'}">${pieceImg}</div>`;
    }
  }
  boardPreview.innerHTML = html;
}

function renderPieceSetGrid() {
  pieceSetGrid.innerHTML = pieceSets.map(ps => `
    <div class="piece-set-card ${currentPieceSet === ps.id ? 'active' : ''}" data-piece-set="${ps.id}">
      ${ps.name}
    </div>
  `).join('');

  pieceSetGrid.querySelectorAll('.piece-set-card').forEach(card => {
    card.addEventListener('click', () => {
      currentPieceSet = card.dataset.pieceSet;
      renderPieceSetGrid();
      renderBoardPreview();
    });
  });
}

function renderBoardColorPresets() {
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

  boardColorPresetsEl.querySelectorAll('.board-color-preset').forEach(preset => {
    preset.addEventListener('click', () => {
      currentBoardLight = preset.dataset.light;
      currentBoardDark = preset.dataset.dark;
      activeBoardColorPreset = preset.dataset.presetId;

      boardLightColor.value = currentBoardLight;
      boardLightHex.value = currentBoardLight.toUpperCase();
      boardDarkColor.value = currentBoardDark;
      boardDarkHex.value = currentBoardDark.toUpperCase();

      renderBoardColorPresets();
      renderBoardPreview();
    });
  });
}

function clearActiveBoardColorPreset() {
  activeBoardColorPreset = null;
  boardColorPresetsEl.querySelectorAll('.board-color-preset').forEach(el => {
    el.classList.remove('active');
  });
}

function checkIfMatchesBoardColorPreset() {
  for (const preset of boardColorPresets) {
    if (preset.light.toLowerCase() === currentBoardLight.toLowerCase() &&
        preset.dark.toLowerCase() === currentBoardDark.toLowerCase()) {
      activeBoardColorPreset = preset.id;
      return;
    }
  }
  activeBoardColorPreset = null;
}

setupColorInput(boardLightColor, boardLightHex, (val) => {
  currentBoardLight = val;
  clearActiveBoardColorPreset();
  renderBoardPreview();
});

setupColorInput(boardDarkColor, boardDarkHex, (val) => {
  currentBoardDark = val;
  clearActiveBoardColorPreset();
  renderBoardPreview();
});

document.getElementById('resetBoardBtn').addEventListener('click', () => {
  currentPieceSet = 'wikipedia';
  currentBoardLight = '#f0d9b5';
  currentBoardDark = '#b58863';

  boardLightColor.value = currentBoardLight;
  boardLightHex.value = currentBoardLight.toUpperCase();
  boardDarkColor.value = currentBoardDark;
  boardDarkHex.value = currentBoardDark.toUpperCase();

  checkIfMatchesBoardColorPreset();
  renderPieceSetGrid();
  renderBoardColorPresets();
  renderBoardPreview();
});

export async function initBoardEditor() {
  try {
    const pieceSetsData = await client.settings.getPieceSets();
    pieceSets = pieceSetsData.piece_sets;

    const colorPresetsData = await client.settings.getBoardColorPresets();
    boardColorPresets = colorPresetsData.presets;

    const settings = await client.settings.getBoard();
    currentPieceSet = settings.piece_set;
    currentBoardLight = settings.board_light;
    currentBoardDark = settings.board_dark;

    boardLightColor.value = currentBoardLight;
    boardLightHex.value = currentBoardLight.toUpperCase();
    boardDarkColor.value = currentBoardDark;
    boardDarkHex.value = currentBoardDark.toUpperCase();

    checkIfMatchesBoardColorPreset();
    renderPieceSetGrid();
    renderBoardColorPresets();
    renderBoardPreview();
  } catch (err) {
    console.error('Failed to load board settings:', err);
  }
}

export async function saveBoardSettings() {
  try {
    await client.settings.saveBoard({
      piece_set: currentPieceSet,
      board_light: currentBoardLight,
      board_dark: currentBoardDark
    });
  } catch (err) {
    console.error('Failed to save board settings:', err);
  }
}
