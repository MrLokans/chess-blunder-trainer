import { setupColorInput } from './color-input.js';

const form = document.getElementById('settingsForm');
const errorAlert = document.getElementById('errorAlert');
const successAlert = document.getElementById('successAlert');
const submitBtn = document.getElementById('submitBtn');
const lichessInput = document.getElementById('lichess');
const chesscomInput = document.getElementById('chesscom');

function showError(message) {
  errorAlert.textContent = message;
  errorAlert.classList.add('visible');
  successAlert.classList.remove('visible');
}

function showSuccess(message) {
  successAlert.textContent = message;
  successAlert.classList.add('visible');
  errorAlert.classList.remove('visible');
}

function hideAlerts() {
  errorAlert.classList.remove('visible');
  successAlert.classList.remove('visible');
}

// Theme color inputs - maps to API field names
const themeInputs = {
  primary: { color: document.getElementById('themePrimary'), hex: document.getElementById('themePrimaryHex') },
  success: { color: document.getElementById('themeSuccess'), hex: document.getElementById('themeSuccessHex') },
  error: { color: document.getElementById('themeError'), hex: document.getElementById('themeErrorHex') },
  warning: { color: document.getElementById('themeWarning'), hex: document.getElementById('themeWarningHex') },
  phase_opening: { color: document.getElementById('themePhaseOpening'), hex: document.getElementById('themePhaseOpeningHex') },
  phase_middlegame: { color: document.getElementById('themePhaseMiddlegame'), hex: document.getElementById('themePhaseMiddlegameHex') },
  phase_endgame: { color: document.getElementById('themePhaseEndgame'), hex: document.getElementById('themePhaseEndgameHex') },
  bg: { color: document.getElementById('themeBg'), hex: document.getElementById('themeBgHex') },
  bg_card: { color: document.getElementById('themeBgCard'), hex: document.getElementById('themeBgCardHex') },
  text: { color: document.getElementById('themeText'), hex: document.getElementById('themeTextHex') },
  text_muted: { color: document.getElementById('themeTextMuted'), hex: document.getElementById('themeTextMutedHex') },
  heatmap_empty: { color: document.getElementById('themeHeatmapEmpty'), hex: document.getElementById('themeHeatmapEmptyHex') },
  heatmap_l1: { color: document.getElementById('themeHeatmapL1'), hex: document.getElementById('themeHeatmapL1Hex') },
  heatmap_l2: { color: document.getElementById('themeHeatmapL2'), hex: document.getElementById('themeHeatmapL2Hex') },
  heatmap_l3: { color: document.getElementById('themeHeatmapL3'), hex: document.getElementById('themeHeatmapL3Hex') },
  heatmap_l4: { color: document.getElementById('themeHeatmapL4'), hex: document.getElementById('themeHeatmapL4Hex') }
};

const defaultTheme = {
  primary: '#4f6d7a',
  success: '#3d8b6e',
  error: '#c25450',
  warning: '#b8860b',
  phase_opening: '#5b8a9a',
  phase_middlegame: '#9a7b5b',
  phase_endgame: '#7a5b9a',
  bg: '#f1f5f9',
  bg_card: '#ffffff',
  text: '#1e293b',
  text_muted: '#64748b',
  heatmap_empty: '#ebedf0',
  heatmap_l1: '#9be9a8',
  heatmap_l2: '#40c463',
  heatmap_l3: '#30a14e',
  heatmap_l4: '#216e39'
};

let themePresets = [];
let activePresetId = null;

function setupColorSync(name) {
  const { color, hex } = themeInputs[name];
  setupColorInput(color, hex, () => {
    updateThemePreview();
    clearActivePreset();
  });
}

function clearActivePreset() {
  activePresetId = null;
  document.querySelectorAll('.preset-card').forEach(card => {
    card.classList.remove('active');
  });
}

// Update live preview
function updateThemePreview() {
  const root = document.documentElement;
  const theme = getCurrentTheme();
  
  // Core colors
  root.style.setProperty('--color-primary', theme.primary);
  root.style.setProperty('--color-success', theme.success);
  root.style.setProperty('--color-error', theme.error);
  root.style.setProperty('--color-warning', theme.warning);
  
  // Phase colors
  root.style.setProperty('--color-phase-opening', theme.phase_opening);
  root.style.setProperty('--color-phase-middlegame', theme.phase_middlegame);
  root.style.setProperty('--color-phase-endgame', theme.phase_endgame);
  
  // Background and text
  root.style.setProperty('--bg', theme.bg);
  root.style.setProperty('--bg-elevated', theme.bg_card);
  root.style.setProperty('--text', theme.text);
  root.style.setProperty('--text-muted', theme.text_muted);
  
  // Heatmap colors
  root.style.setProperty('--heatmap-empty', theme.heatmap_empty);
  root.style.setProperty('--heatmap-l1', theme.heatmap_l1);
  root.style.setProperty('--heatmap-l2', theme.heatmap_l2);
  root.style.setProperty('--heatmap-l3', theme.heatmap_l3);
  root.style.setProperty('--heatmap-l4', theme.heatmap_l4);
  
  // Update derived colors
  if (window.adjustColor) {
    root.style.setProperty('--color-primary-hover', window.adjustColor(theme.primary, -15));
    root.style.setProperty('--color-primary-muted', window.adjustColor(theme.primary, 20));
    root.style.setProperty('--color-success-bg', window.adjustColor(theme.success, 85, 0.15));
    root.style.setProperty('--color-success-border', window.adjustColor(theme.success, 50, 0.4));
    root.style.setProperty('--color-error-bg', window.adjustColor(theme.error, 85, 0.15));
    root.style.setProperty('--color-error-border', window.adjustColor(theme.error, 50, 0.4));
    root.style.setProperty('--color-warning-bg', window.adjustColor(theme.warning, 85, 0.15));
    root.style.setProperty('--color-warning-border', window.adjustColor(theme.warning, 50, 0.4));
  }
}

function getCurrentTheme() {
  const theme = {};
  for (const [name, inputs] of Object.entries(themeInputs)) {
    theme[name] = inputs.hex.value;
  }
  return theme;
}

function setThemeInputs(theme) {
  for (const [name, value] of Object.entries(theme)) {
    if (themeInputs[name]) {
      themeInputs[name].color.value = value;
      themeInputs[name].hex.value = value.toUpperCase();
    }
  }
  updateThemePreview();
}

// Setup color syncing
Object.keys(themeInputs).forEach(setupColorSync);

// Load and render presets
async function loadPresets() {
  try {
    const resp = await fetch('/api/settings/theme/presets');
    if (resp.ok) {
      const data = await resp.json();
      themePresets = data.presets;
      renderPresets();
    }
  } catch (err) {
    console.error('Failed to load presets:', err);
  }
}

function renderPresets() {
  const grid = document.getElementById('presetGrid');
  grid.innerHTML = themePresets.map(preset => `
    <div class="preset-card ${activePresetId === preset.id ? 'active' : ''}" data-preset-id="${preset.id}">
      <div class="preset-colors">
        <span class="preset-color-dot" style="background: ${preset.colors.primary}"></span>
        <span class="preset-color-dot" style="background: ${preset.colors.success}"></span>
        <span class="preset-color-dot" style="background: ${preset.colors.error}"></span>
        <span class="preset-color-dot" style="background: ${preset.colors.bg}"></span>
      </div>
      <div class="preset-name">${preset.name}</div>
    </div>
  `).join('');

  // Add click handlers
  grid.querySelectorAll('.preset-card').forEach(card => {
    card.addEventListener('click', () => {
      const presetId = card.dataset.presetId;
      applyPreset(presetId);
    });
  });
}

function applyPreset(presetId) {
  const preset = themePresets.find(p => p.id === presetId);
  if (!preset) return;

  activePresetId = presetId;
  setThemeInputs(preset.colors);
  
  // Update active state in UI
  document.querySelectorAll('.preset-card').forEach(card => {
    card.classList.toggle('active', card.dataset.presetId === presetId);
  });
}

function checkIfMatchesPreset() {
  const currentTheme = getCurrentTheme();
  for (const preset of themePresets) {
    const matches = Object.keys(currentTheme).every(
      key => currentTheme[key].toLowerCase() === preset.colors[key].toLowerCase()
    );
    if (matches) {
      activePresetId = preset.id;
      return;
    }
  }
  activePresetId = null;
}

// Reset theme button
document.getElementById('resetThemeBtn').addEventListener('click', async () => {
  applyPreset('default');
});

// Load sync settings and theme
async function loadSyncSettings() {
  try {
    // Load presets first
    await loadPresets();

    // Load theme colors
    const themeResp = await fetch('/api/settings/theme');
    if (themeResp.ok) {
      const theme = await themeResp.json();
      setThemeInputs(theme);
      checkIfMatchesPreset();
      renderPresets(); // Re-render to show active state
    }

    // Load all settings from API
    const settingsResp = await fetch('/api/settings');
    if (settingsResp.ok) {
      const settings = await settingsResp.json();
      document.getElementById('autoSync').checked = settings.auto_sync;
      document.getElementById('syncInterval').value = String(settings.sync_interval);
      document.getElementById('maxGames').value = String(settings.max_games);
      document.getElementById('autoAnalyze').checked = settings.auto_analyze;
      document.getElementById('spacedRepetitionDays').value = String(settings.spaced_repetition_days);
    }
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  hideAlerts();

  const lichess = lichessInput.value.trim();
  const chesscom = chesscomInput.value.trim();

  // Validate at least one username
  if (!lichess && !chesscom) {
    showError('Please provide at least one username (Lichess or Chess.com)');
    return;
  }

  // Get sync settings
  const autoSync = document.getElementById('autoSync').checked;
  const syncInterval = document.getElementById('syncInterval').value;
  const maxGames = document.getElementById('maxGames').value;
  const autoAnalyze = document.getElementById('autoAnalyze').checked;
  const spacedRepetitionDays = document.getElementById('spacedRepetitionDays').value;

  submitBtn.disabled = true;
  submitBtn.textContent = 'Saving...';

  try {
    const theme = getCurrentTheme();
    
    const response = await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lichess,
        chesscom,
        auto_sync: autoSync,
        sync_interval: syncInterval,
        max_games: maxGames,
        auto_analyze: autoAnalyze,
        spaced_repetition_days: spacedRepetitionDays,
        theme
      })
    });
    
    // Update localStorage with new theme
    localStorage.setItem('theme', JSON.stringify(theme));

    const data = await response.json();

    if (response.ok) {
      showSuccess('Settings saved successfully!');
      setTimeout(() => {
        window.location.href = '/';
      }, 1500);
    } else {
      showError(data.error || 'Failed to save settings. Please try again.');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Save Changes';
    }
  } catch (err) {
    showError('Network error. Please try again.');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Save Changes';
    console.error(err);
  }
});

// ==================== Board Settings ====================

// Board settings state
let pieceSets = [];
let boardColorPresets = [];
let currentPieceSet = 'wikipedia';
let currentBoardLight = '#f0d9b5';
let currentBoardDark = '#b58863';
let activeBoardColorPreset = null;

// Board settings DOM elements
const boardPreview = document.getElementById('boardPreview');
const pieceSetGrid = document.getElementById('pieceSetGrid');
const boardColorPresetsEl = document.getElementById('boardColorPresets');
const boardLightColor = document.getElementById('boardLightColor');
const boardLightHex = document.getElementById('boardLightHex');
const boardDarkColor = document.getElementById('boardDarkColor');
const boardDarkHex = document.getElementById('boardDarkHex');
const resetBoardBtn = document.getElementById('resetBoardBtn');

// Preview board pieces (simplified 4x4)
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
      const light = preset.dataset.light;
      const dark = preset.dataset.dark;
      const presetId = preset.dataset.presetId;
      
      currentBoardLight = light;
      currentBoardDark = dark;
      activeBoardColorPreset = presetId;
      
      boardLightColor.value = light;
      boardLightHex.value = light.toUpperCase();
      boardDarkColor.value = dark;
      boardDarkHex.value = dark.toUpperCase();
      
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

// Reset board settings
resetBoardBtn.addEventListener('click', async () => {
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

// Load board settings
async function loadBoardSettings() {
  try {
    // Load piece sets
    const pieceSetsResp = await fetch('/api/settings/board/piece-sets');
    if (pieceSetsResp.ok) {
      const data = await pieceSetsResp.json();
      pieceSets = data.piece_sets;
    }

    // Load color presets
    const colorPresetsResp = await fetch('/api/settings/board/color-presets');
    if (colorPresetsResp.ok) {
      const data = await colorPresetsResp.json();
      boardColorPresets = data.presets;
    }

    // Load current settings
    const boardResp = await fetch('/api/settings/board');
    if (boardResp.ok) {
      const settings = await boardResp.json();
      currentPieceSet = settings.piece_set;
      currentBoardLight = settings.board_light;
      currentBoardDark = settings.board_dark;
      
      boardLightColor.value = currentBoardLight;
      boardLightHex.value = currentBoardLight.toUpperCase();
      boardDarkColor.value = currentBoardDark;
      boardDarkHex.value = currentBoardDark.toUpperCase();
    }

    checkIfMatchesBoardColorPreset();
    renderPieceSetGrid();
    renderBoardColorPresets();
    renderBoardPreview();
  } catch (err) {
    console.error('Failed to load board settings:', err);
  }
}

// Save board settings (called from form submit)
async function saveBoardSettings() {
  try {
    await fetch('/api/settings/board', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        piece_set: currentPieceSet,
        board_light: currentBoardLight,
        board_dark: currentBoardDark
      })
    });
  } catch (err) {
    console.error('Failed to save board settings:', err);
  }
}

// Modify the form submit to also save board settings
const originalFormSubmit = form.onsubmit;
form.addEventListener('submit', async (e) => {
  // Board settings are saved separately
  await saveBoardSettings();
});

// Load settings on page load
loadSyncSettings();
loadBoardSettings();
