import { useCallback, useEffect } from 'preact/hooks';
import { Button } from '../components/primitives/Button';
import { ColorInput } from '../components/primitives/ColorInput';
import { readBoardColors } from '../shared/board-theme';
import type { PieceSet, BoardColorPreset, BoardSettings } from './types';

interface BoardEditorProps {
  pieceSets: PieceSet[];
  colorPresets: BoardColorPreset[];
  settings: BoardSettings;
  onChange: (settings: BoardSettings) => void;
}

const PREVIEW_PIECES: (string | null)[][] = [
  ['bR', null, 'bB', 'bK'],
  [null, 'bP', null, 'bP'],
  ['wP', null, 'wN', null],
  ['wR', null, 'wB', 'wK'],
];

export function BoardEditor({ pieceSets, colorPresets, settings, onChange }: BoardEditorProps) {
  // null means "never customised" — the board follows the mode-aware default
  // from tokens.css, which is what the inputs and preview should show.
  const fallback = readBoardColors();
  const light = settings.board_light ?? fallback.light;
  const dark = settings.board_dark ?? fallback.dark;

  const activeColorPreset = colorPresets.find(
    p => p.light.toLowerCase() === light.toLowerCase()
      && p.dark.toLowerCase() === dark.toLowerCase(),
  )?.id ?? null;

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--preview-board-light', light);
    root.style.setProperty('--preview-board-dark', dark);
  }, [light, dark]);

  const handlePieceSetClick = useCallback((id: string) => {
    onChange({ ...settings, piece_set: id });
  }, [settings, onChange]);

  const handleColorPresetClick = useCallback((preset: BoardColorPreset) => {
    onChange({ ...settings, board_light: preset.light, board_dark: preset.dark });
  }, [settings, onChange]);

  const handleLightChange = useCallback((value: string) => {
    onChange({ ...settings, board_light: value, board_dark: dark });
  }, [settings, dark, onChange]);

  const handleDarkChange = useCallback((value: string) => {
    onChange({ ...settings, board_light: light, board_dark: value });
  }, [settings, light, onChange]);

  // Clearing the colours (rather than writing the light-mode pair) is what puts
  // the board back on the mode-aware default.
  const handleReset = useCallback(() => {
    onChange({ piece_set: 'gioco', board_light: null, board_dark: null });
  }, [onChange]);

  return (
    <>
      <h2 class="settings-section-title">{t('settings.board.title')}</h2>
      <p class="help-text mb-4">{t('settings.board.description')}</p>

      <div class="board-preview-container">
        <div class="board-preview">
          {PREVIEW_PIECES.map((row, ri) =>
            row.map((piece, ci) => {
              const isLight = (ri + ci) % 2 === 0;
              return (
                <div class={`square ${isLight ? 'light' : 'dark'}`} key={`${String(ri)}-${String(ci)}`}>
                  {piece && (
                    <img src={`/static/pieces/${settings.piece_set}/${piece}.svg`} alt={piece} />
                  )}
                </div>
              );
            }),
          )}
        </div>

        <div class="board-settings-controls">
          <label class="theme-section-title">{t('settings.board.piece_set')}</label>
          <div class="piece-set-grid">
            {pieceSets.map(ps => (
              <div
                key={ps.id}
                class={`piece-set-card ${settings.piece_set === ps.id ? 'active' : ''}`}
                onClick={() => { handlePieceSetClick(ps.id); }}
              >
                {ps.name}
              </div>
            ))}
          </div>

          <label class="theme-section-title">{t('settings.board.colors')}</label>
          <div class="board-color-presets">
            {colorPresets.map(preset => (
              <div
                key={preset.id}
                class={`board-color-preset ${activeColorPreset === preset.id ? 'active' : ''}`}
                title={preset.name}
                onClick={() => { handleColorPresetClick(preset); }}
              >
                <div class="light" style={{ background: preset.light }} />
                <div class="light-alt" style={{ background: preset.dark }} />
                <div class="dark-alt" style={{ background: preset.light }} />
                <div class="dark" style={{ background: preset.dark }} />
              </div>
            ))}
          </div>

          <div class="board-custom-colors">
            <div class="form-group mb-0">
              <label>{t('settings.board.light_squares')}</label>
              <div class="color-input-row">
                <ColorInput value={light} onChange={handleLightChange} />
              </div>
            </div>
            <div class="form-group mb-0">
              <label>{t('settings.board.dark_squares')}</label>
              <div class="color-input-row">
                <ColorInput value={dark} onChange={handleDarkChange} />
              </div>
            </div>
          </div>

          <div class="mt-3">
            <Button variant="secondary" onClick={handleReset}>
              {t('settings.board.reset')}
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
