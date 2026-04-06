import { setupColorInput } from '../shared/color-input';
import { client } from '../shared/api';

interface ThemeInputPair {
  color: HTMLInputElement | null;
  hex: HTMLInputElement | null;
}

interface ThemePreset {
  id: string;
  name: string;
  colors: Record<string, string>;
}

declare global {
  interface Window {
    adjustColor?: (hex: string, lightness: number, saturation?: number) => string;
  }
}

const themeInputs: Record<string, ThemeInputPair> = {
  primary: { color: document.getElementById('themePrimary') as HTMLInputElement | null, hex: document.getElementById('themePrimaryHex') as HTMLInputElement | null },
  success: { color: document.getElementById('themeSuccess') as HTMLInputElement | null, hex: document.getElementById('themeSuccessHex') as HTMLInputElement | null },
  error: { color: document.getElementById('themeError') as HTMLInputElement | null, hex: document.getElementById('themeErrorHex') as HTMLInputElement | null },
  warning: { color: document.getElementById('themeWarning') as HTMLInputElement | null, hex: document.getElementById('themeWarningHex') as HTMLInputElement | null },
  phase_opening: { color: document.getElementById('themePhaseOpening') as HTMLInputElement | null, hex: document.getElementById('themePhaseOpeningHex') as HTMLInputElement | null },
  phase_middlegame: { color: document.getElementById('themePhaseMiddlegame') as HTMLInputElement | null, hex: document.getElementById('themePhaseMiddlegameHex') as HTMLInputElement | null },
  phase_endgame: { color: document.getElementById('themePhaseEndgame') as HTMLInputElement | null, hex: document.getElementById('themePhaseEndgameHex') as HTMLInputElement | null },
  bg: { color: document.getElementById('themeBg') as HTMLInputElement | null, hex: document.getElementById('themeBgHex') as HTMLInputElement | null },
  bg_card: { color: document.getElementById('themeBgCard') as HTMLInputElement | null, hex: document.getElementById('themeBgCardHex') as HTMLInputElement | null },
  text: { color: document.getElementById('themeText') as HTMLInputElement | null, hex: document.getElementById('themeTextHex') as HTMLInputElement | null },
  text_muted: { color: document.getElementById('themeTextMuted') as HTMLInputElement | null, hex: document.getElementById('themeTextMutedHex') as HTMLInputElement | null },
  heatmap_empty: { color: document.getElementById('themeHeatmapEmpty') as HTMLInputElement | null, hex: document.getElementById('themeHeatmapEmptyHex') as HTMLInputElement | null },
  heatmap_l1: { color: document.getElementById('themeHeatmapL1') as HTMLInputElement | null, hex: document.getElementById('themeHeatmapL1Hex') as HTMLInputElement | null },
  heatmap_l2: { color: document.getElementById('themeHeatmapL2') as HTMLInputElement | null, hex: document.getElementById('themeHeatmapL2Hex') as HTMLInputElement | null },
  heatmap_l3: { color: document.getElementById('themeHeatmapL3') as HTMLInputElement | null, hex: document.getElementById('themeHeatmapL3Hex') as HTMLInputElement | null },
  heatmap_l4: { color: document.getElementById('themeHeatmapL4') as HTMLInputElement | null, hex: document.getElementById('themeHeatmapL4Hex') as HTMLInputElement | null },
};

let themePresets: ThemePreset[] = [];
let activePresetId: string | null = null;

function clearActivePreset(): void {
  activePresetId = null;
  document.querySelectorAll('.preset-card').forEach(card => {
    card.classList.remove('active');
  });
}

function updateThemePreview(): void {
  const root = document.documentElement;
  const theme = getCurrentTheme();

  root.style.setProperty('--color-primary', theme.primary ?? '');
  root.style.setProperty('--color-success', theme.success ?? '');
  root.style.setProperty('--color-error', theme.error ?? '');
  root.style.setProperty('--color-warning', theme.warning ?? '');

  root.style.setProperty('--color-phase-opening', theme.phase_opening ?? '');
  root.style.setProperty('--color-phase-middlegame', theme.phase_middlegame ?? '');
  root.style.setProperty('--color-phase-endgame', theme.phase_endgame ?? '');

  root.style.setProperty('--bg', theme.bg ?? '');
  root.style.setProperty('--bg-elevated', theme.bg_card ?? '');
  root.style.setProperty('--text', theme.text ?? '');
  root.style.setProperty('--text-muted', theme.text_muted ?? '');

  root.style.setProperty('--heatmap-empty', theme.heatmap_empty ?? '');
  root.style.setProperty('--heatmap-l1', theme.heatmap_l1 ?? '');
  root.style.setProperty('--heatmap-l2', theme.heatmap_l2 ?? '');
  root.style.setProperty('--heatmap-l3', theme.heatmap_l3 ?? '');
  root.style.setProperty('--heatmap-l4', theme.heatmap_l4 ?? '');

  if (window.adjustColor) {
    root.style.setProperty('--color-primary-hover', window.adjustColor(theme.primary ?? '', -15));
    root.style.setProperty('--color-primary-muted', window.adjustColor(theme.primary ?? '', 20));
    root.style.setProperty('--color-success-bg', window.adjustColor(theme.success ?? '', 85, 0.15));
    root.style.setProperty('--color-success-border', window.adjustColor(theme.success ?? '', 50, 0.4));
    root.style.setProperty('--color-error-bg', window.adjustColor(theme.error ?? '', 85, 0.15));
    root.style.setProperty('--color-error-border', window.adjustColor(theme.error ?? '', 50, 0.4));
    root.style.setProperty('--color-warning-bg', window.adjustColor(theme.warning ?? '', 85, 0.15));
    root.style.setProperty('--color-warning-border', window.adjustColor(theme.warning ?? '', 50, 0.4));
  }
}

export function getCurrentTheme(): Record<string, string> {
  const theme: Record<string, string> = {};
  for (const [name, inputs] of Object.entries(themeInputs)) {
    theme[name] = inputs.hex?.value ?? '';
  }
  return theme;
}

function setThemeInputs(theme: Record<string, string>): void {
  for (const [name, value] of Object.entries(theme)) {
    const inputs = themeInputs[name];
    if (inputs) {
      if (inputs.color) inputs.color.value = value;
      if (inputs.hex) inputs.hex.value = value.toUpperCase();
    }
  }
  updateThemePreview();
}

Object.keys(themeInputs).forEach(name => {
  const inputs = themeInputs[name]!;
  if (inputs.color && inputs.hex) {
    setupColorInput(inputs.color, inputs.hex, () => {
      updateThemePreview();
      clearActivePreset();
    });
  }
});

async function loadPresets(): Promise<void> {
  try {
    const data = await client.settings.getThemePresets() as { presets: ThemePreset[] };
    themePresets = data.presets;
    renderPresets();
  } catch (err) {
    console.error('Failed to load presets:', err);
  }
}

function renderPresets(): void {
  const grid = document.getElementById('presetGrid');
  if (!grid) return;
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

  grid.querySelectorAll<HTMLElement>('.preset-card').forEach(card => {
    card.addEventListener('click', () => {
      applyPreset(card.dataset.presetId ?? '');
    });
  });
}

function applyPreset(presetId: string): void {
  const preset = themePresets.find(p => p.id === presetId);
  if (!preset) return;

  activePresetId = presetId;
  setThemeInputs(preset.colors);

  document.querySelectorAll<HTMLElement>('.preset-card').forEach(card => {
    card.classList.toggle('active', card.dataset.presetId === presetId);
  });
}

function checkIfMatchesPreset(): void {
  const currentTheme = getCurrentTheme();
  for (const preset of themePresets) {
    const matches = Object.keys(currentTheme).every(
      key => (currentTheme[key] ?? '').toLowerCase() === (preset.colors[key] ?? '').toLowerCase(),
    );
    if (matches) {
      activePresetId = preset.id;
      return;
    }
  }
  activePresetId = null;
}

document.getElementById('resetThemeBtn')?.addEventListener('click', () => {
  applyPreset('default');
});

export async function initThemeEditor(): Promise<void> {
  await loadPresets();
  const theme = await client.settings.getTheme() as Record<string, string>;
  setThemeInputs(theme);
  checkIfMatchesPreset();
  renderPresets();
}
