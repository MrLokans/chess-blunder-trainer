import { useCallback, useEffect, useMemo } from 'preact/hooks';
import { ColorInput } from '../components/ColorInput';
import { THEME_COLOR_KEYS } from './types';
import type { ThemeColorKey, ThemeColors, ThemePreset } from './types';

interface ThemeEditorProps {
  theme: ThemeColors;
  presets: ThemePreset[];
  onChange: (theme: ThemeColors) => void;
}

const SECTIONS: Array<{ titleKey: string; keys: readonly ThemeColorKey[] }> = [
  { titleKey: 'settings.theme.accent', keys: ['primary', 'success', 'error', 'warning'] },
  { titleKey: 'settings.theme.phases', keys: ['phase_opening', 'phase_middlegame', 'phase_endgame'] },
  { titleKey: 'settings.theme.bg_text', keys: ['bg', 'bg_card', 'text', 'text_muted'] },
  { titleKey: 'settings.theme.heatmap', keys: ['heatmap_empty', 'heatmap_l1', 'heatmap_l2', 'heatmap_l3', 'heatmap_l4'] },
];

const COLOR_LABELS: Record<ThemeColorKey, string> = {
  primary: 'settings.theme.primary', success: 'settings.theme.success',
  error: 'settings.theme.error_label', warning: 'settings.theme.warning',
  phase_opening: 'chess.phase.opening', phase_middlegame: 'chess.phase.middlegame',
  phase_endgame: 'chess.phase.endgame', bg: 'settings.theme.bg',
  bg_card: 'settings.theme.bg_card', text: 'settings.theme.text',
  text_muted: 'settings.theme.text_muted', heatmap_empty: 'settings.theme.heatmap_empty',
  heatmap_l1: 'settings.theme.heatmap_l1', heatmap_l2: 'settings.theme.heatmap_l2',
  heatmap_l3: 'settings.theme.heatmap_l3', heatmap_l4: 'settings.theme.heatmap_l4',
};

const COLOR_HELP: Partial<Record<ThemeColorKey, string>> = {
  primary: 'settings.theme.primary_help',
  success: 'settings.theme.success_help',
  error: 'settings.theme.error_help',
  warning: 'settings.theme.warning_help',
};

const HEATMAP_GRID = [
  [0, 1, 0, 2, 0, 1, 0],
  [1, 2, 3, 1, 0, 2, 1],
  [0, 3, 4, 3, 2, 1, 0],
  [2, 4, 3, 4, 2, 3, 1],
  [1, 2, 1, 3, 2, 0, 1],
  [0, 1, 0, 2, 1, 0, 0],
];

export function ThemeEditor({ theme, presets, onChange }: ThemeEditorProps) {
  const activePresetId = useMemo(() => {
    for (const preset of presets) {
      const matches = THEME_COLOR_KEYS.every(
        key => theme[key].toLowerCase() === preset.colors[key].toLowerCase(),
      );
      if (matches) return preset.id;
    }
    return null;
  }, [theme, presets]);

  useEffect(() => {
    applyThemePreview(theme);
  }, [theme]);

  const handleColorChange = useCallback((key: ThemeColorKey, value: string) => {
    onChange({ ...theme, [key]: value });
  }, [theme, onChange]);

  const handlePresetClick = useCallback((presetId: string) => {
    const preset = presets.find(p => p.id === presetId);
    if (!preset) return;
    onChange({ ...preset.colors });
  }, [presets, onChange]);

  const handleReset = useCallback(() => {
    handlePresetClick('default');
  }, [handlePresetClick]);

  return (
    <div class="theme-colors">
      <div class="preset-selector">
        <label class="theme-section-title">{t('settings.theme.presets')}</label>
        <div class="preset-grid">
          {presets.map(preset => (
            <div
              key={preset.id}
              class={`preset-card ${activePresetId === preset.id ? 'active' : ''}`}
              onClick={() => { handlePresetClick(preset.id); }}
            >
              <div class="preset-colors">
                <span class="preset-color-dot" style={{ background: preset.colors.primary }} />
                <span class="preset-color-dot" style={{ background: preset.colors.success }} />
                <span class="preset-color-dot" style={{ background: preset.colors.error }} />
                <span class="preset-color-dot" style={{ background: preset.colors.bg }} />
              </div>
              <div class="preset-name">{preset.name}</div>
            </div>
          ))}
        </div>
      </div>

      {SECTIONS.map(section => (
        <div class="theme-color-section" key={section.titleKey}>
          <h3 class="theme-section-title">{t(section.titleKey)}</h3>
          <div class="color-grid">
            {section.keys.map(key => (
              <div class="form-group" key={key}>
                <label>{t(COLOR_LABELS[key])}</label>
                <div class="color-input-row">
                  <ColorInput
                    value={theme[key]}
                    onChange={(val) => { handleColorChange(key, val); }}
                  />
                </div>
                {COLOR_HELP[key] && <div class="help-text">{t(COLOR_HELP[key])}</div>}
              </div>
            ))}
          </div>
        </div>
      ))}

      <ThemePreview />
      <button type="button" class="btn btn-secondary mt-3" onClick={handleReset}>
        {t('settings.theme.reset')}
      </button>
    </div>
  );
}

function ThemePreview() {
  return (
    <div class="theme-preview">
      <div class="preview-label">{t('settings.theme.preview')}</div>
      <div class="preview-buttons">
        <button type="button" class="btn preview-primary">{t('settings.theme.primary')}</button>
        <button type="button" class="btn btn-success preview-success">{t('settings.theme.success')}</button>
        <button type="button" class="btn btn-danger preview-error">{t('settings.theme.error_label')}</button>
        <span class="status preview-warning">{t('settings.theme.warning')}</span>
      </div>
      <div class="preview-phases">
        <span class="phase-pill opening">{t('chess.phase.opening')}</span>
        <span class="phase-pill middlegame">{t('chess.phase.middlegame')}</span>
        <span class="phase-pill endgame">{t('chess.phase.endgame')}</span>
      </div>
      <div class="preview-heatmap">
        <div class="preview-heatmap-label">{t('settings.theme.heatmap')}</div>
        <div class="preview-heatmap-grid">
          {HEATMAP_GRID.map((week, wi) => (
            <div class="preview-heatmap-week" key={wi}>
              {week.map((level, di) => (
                <div class={`preview-heatmap-cell level-${String(level)}`} key={di} />
              ))}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function applyThemePreview(theme: ThemeColors): void {
  const root = document.documentElement;
  const cssMap: Record<string, string> = {
    '--color-primary': theme.primary, '--color-success': theme.success,
    '--color-error': theme.error, '--color-warning': theme.warning,
    '--color-phase-opening': theme.phase_opening,
    '--color-phase-middlegame': theme.phase_middlegame,
    '--color-phase-endgame': theme.phase_endgame,
    '--bg': theme.bg, '--bg-elevated': theme.bg_card,
    '--text': theme.text, '--text-muted': theme.text_muted,
    '--heatmap-empty': theme.heatmap_empty, '--heatmap-l1': theme.heatmap_l1,
    '--heatmap-l2': theme.heatmap_l2, '--heatmap-l3': theme.heatmap_l3,
    '--heatmap-l4': theme.heatmap_l4,
  };

  for (const [prop, value] of Object.entries(cssMap)) {
    root.style.setProperty(prop, value);
  }

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
