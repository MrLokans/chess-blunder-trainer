import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { BoardEditor } from '../../src/settings/BoardEditor';
import type { PieceSet, BoardColorPreset, BoardSettings } from '../../src/settings/types';

const PIECE_SETS: PieceSet[] = [
  { id: 'gioco', name: 'Gioco' },
  { id: 'merida', name: 'Merida' },
];

const COLOR_PRESETS: BoardColorPreset[] = [
  { id: 'brown', name: 'Brown', light: '#f0d9b5', dark: '#b58863' },
  { id: 'blue', name: 'Blue', light: '#dee3e6', dark: '#8ca2ad' },
];

const SETTINGS: BoardSettings = {
  piece_set: 'gioco',
  board_light: '#f0d9b5',
  board_dark: '#b58863',
};

describe('BoardEditor', () => {
  test('renders piece set options', () => {
    render(<BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={SETTINGS} onChange={() => {}} />);
    expect(screen.getByText('Gioco')).toBeDefined();
    expect(screen.getByText('Merida')).toBeDefined();
  });

  test('marks active piece set', () => {
    const { container } = render(
      <BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={SETTINGS} onChange={() => {}} />
    );
    const activeCard = container.querySelector('.piece-set-card.active');
    expect((activeCard as HTMLElement).textContent.trim()).toBe('Gioco');
  });

  test('calls onChange when piece set is selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={SETTINGS} onChange={onChange} />);

    await user.click(screen.getByText('Merida'));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ piece_set: 'merida' }));
  });

  test('calls onChange when color preset is clicked', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={SETTINGS} onChange={onChange} />);

    const bluePreset = screen.getByTitle('Blue');
    await user.click(bluePreset);
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({
      board_light: '#dee3e6',
      board_dark: '#8ca2ad',
    }));
  });

  test('renders 4x4 board preview', () => {
    const { container } = render(
      <BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={SETTINGS} onChange={() => {}} />
    );
    const squares = container.querySelectorAll('.square');
    expect(squares.length).toBe(16);
  });

  test('resets to defaults on reset button click', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(
      <BoardEditor
        pieceSets={PIECE_SETS}
        colorPresets={COLOR_PRESETS}
        settings={{ piece_set: 'merida', board_light: '#111111', board_dark: '#222222' }}
        onChange={onChange}
      />
    );

    await user.click(screen.getByText(t('settings.board.reset')));
    expect(onChange).toHaveBeenCalledWith({
      piece_set: 'gioco',
      board_light: '#E0E0E0',
      board_dark: '#A0A0A0',
    });
  });
});
