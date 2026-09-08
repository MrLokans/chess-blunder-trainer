import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
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

  test('reset clears the colours so the board follows the mode-aware default', async () => {
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
      board_light: null,
      board_dark: null,
    });
  });

  describe('uncustomised colours', () => {
    const UNSET: BoardSettings = { piece_set: 'gioco', board_light: null, board_dark: null };

    beforeEach(() => {
      // Stands in for the mode-aware default that tokens.css supplies in a real
      // browser; jsdom does not resolve light-dark() from a stylesheet.
      document.documentElement.style.setProperty('--board-light', '#A9A297');
      document.documentElement.style.setProperty('--board-dark', '#6E675C');
    });

    afterEach(() => {
      document.documentElement.style.removeProperty('--board-light');
      document.documentElement.style.removeProperty('--board-dark');
    });

    test('shows the resolved default in the colour inputs', () => {
      const { container } = render(
        <BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={UNSET} onChange={() => {}} />
      );
      const values = Array.from(container.querySelectorAll('input')).map(i => i.value.toLowerCase());
      expect(values).toContain('#a9a297');
      expect(values).toContain('#6e675c');
    });

    test('editing one square colour pins the other so the stored pair is never half-set', async () => {
      const onChange = vi.fn();
      const user = userEvent.setup();
      const { container } = render(
        <BoardEditor pieceSets={PIECE_SETS} colorPresets={COLOR_PRESETS} settings={UNSET} onChange={onChange} />
      );

      const hexInput = Array.from(container.querySelectorAll('input')).find(
        i => i.type === 'text' && i.value.toLowerCase() === '#a9a297',
      );
      await user.clear(hexInput as HTMLInputElement);
      await user.type(hexInput as HTMLInputElement, '#ABCDEF');

      const last = onChange.mock.calls.at(-1)?.[0] as BoardSettings;
      expect(last.board_dark).toBe('#6E675C');
    });
  });
});
