import { useCallback, useEffect } from 'preact/hooks';
import { ColorInput } from '../components/ColorInput';
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

const BOARD_DEFAULTS: BoardSettings = {
  piece_set: 'gioco',
  board_light: '#E0E0E0',
  board_dark: '#A0A0A0',
};

export function BoardEditor({ pieceSets, colorPresets, settings, onChange }: BoardEditorProps) {
  const activeColorPreset = colorPresets.find(
    p => p.light.toLowerCase() === settings.board_light.toLowerCase()
      && p.dark.toLowerCase() === settings.board_dark.toLowerCase(),
  )?.id ?? null;

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--preview-board-light', settings.board_light);
    root.style.setProperty('--preview-board-dark', settings.board_dark);
  }, [settings.board_light, settings.board_dark]);

  const handlePieceSetClick = useCallback((id: string) => {
    onChange({ ...settings, piece_set: id });
  }, [settings, onChange]);

  const handleColorPresetClick = useCallback((preset: BoardColorPreset) => {
    onChange({ ...settings, board_light: preset.light, board_dark: preset.dark });
  }, [settings, onChange]);

  const handleLightChange = useCallback((value: string) => {
    onChange({ ...settings, board_light: value });
  }, [settings, onChange]);

  const handleDarkChange = useCallback((value: string) => {
    onChange({ ...settings, board_dark: value });
  }, [settings, onChange]);

  const handleReset = useCallback(() => {
    onChange({ ...BOARD_DEFAULTS });
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
                <ColorInput value={settings.board_light} onChange={handleLightChange} />
              </div>
            </div>
            <div class="form-group mb-0">
              <label>{t('settings.board.dark_squares')}</label>
              <div class="color-input-row">
                <ColorInput value={settings.board_dark} onChange={handleDarkChange} />
              </div>
            </div>
          </div>

          <button type="button" class="btn btn-secondary mt-3" onClick={handleReset}>
            {t('settings.board.reset')}
          </button>
        </div>
      </div>
    </>
  );
}
