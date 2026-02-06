import { setupColorInput } from '../color-input.js';
import { client } from '../api.js';

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

let themePresets = [];
let activePresetId = null;

function clearActivePreset() {
  activePresetId = null;
  document.querySelectorAll('.preset-card').forEach(card => {
    card.classList.remove('active');
  });
}

function updateThemePreview() {
  const root = document.documentElement;
  const theme = getCurrentTheme();

  root.style.setProperty('--color-primary', theme.primary);
  root.style.setProperty('--color-success', theme.success);
  root.style.setProperty('--color-error', theme.error);
  root.style.setProperty('--color-warning', theme.warning);

  root.style.setProperty('--color-phase-opening', theme.phase_opening);
  root.style.setProperty('--color-phase-middlegame', theme.phase_middlegame);
  root.style.setProperty('--color-phase-endgame', theme.phase_endgame);

  root.style.setProperty('--bg', theme.bg);
  root.style.setProperty('--bg-elevated', theme.bg_card);
  root.style.setProperty('--text', theme.text);
  root.style.setProperty('--text-muted', theme.text_muted);

  root.style.setProperty('--heatmap-empty', theme.heatmap_empty);
  root.style.setProperty('--heatmap-l1', theme.heatmap_l1);
  root.style.setProperty('--heatmap-l2', theme.heatmap_l2);
  root.style.setProperty('--heatmap-l3', theme.heatmap_l3);
  root.style.setProperty('--heatmap-l4', theme.heatmap_l4);

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

export function getCurrentTheme() {
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

// Setup color syncing for all theme inputs
Object.keys(themeInputs).forEach(name => {
  const { color, hex } = themeInputs[name];
  setupColorInput(color, hex, () => {
    updateThemePreview();
    clearActivePreset();
  });
});

async function loadPresets() {
  try {
    const data = await client.settings.getThemePresets();
    themePresets = data.presets;
    renderPresets();
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

  grid.querySelectorAll('.preset-card').forEach(card => {
    card.addEventListener('click', () => {
      applyPreset(card.dataset.presetId);
    });
  });
}

function applyPreset(presetId) {
  const preset = themePresets.find(p => p.id === presetId);
  if (!preset) return;

  activePresetId = presetId;
  setThemeInputs(preset.colors);

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

document.getElementById('resetThemeBtn').addEventListener('click', () => {
  applyPreset('default');
});

export async function initThemeEditor() {
  await loadPresets();
  const theme = await client.settings.getTheme();
  setThemeInputs(theme);
  checkIfMatchesPreset();
  renderPresets();
}
