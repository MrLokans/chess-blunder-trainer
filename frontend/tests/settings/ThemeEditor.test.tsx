import { describe, test, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ThemeEditor } from '../../src/settings/ThemeEditor';
import type { ThemeColors, ThemePreset } from '../../src/settings/types';

const MOCK_THEME: ThemeColors = {
  primary: '#4f6d7a', success: '#3d8b6e', error: '#c25450', warning: '#b8860b',
  phase_opening: '#5b8a9a', phase_middlegame: '#9a7b5b', phase_endgame: '#7a5b9a',
  bg: '#f1f5f9', bg_card: '#ffffff', text: '#1e293b', text_muted: '#64748b',
  heatmap_empty: '#ebedf0', heatmap_l1: '#9be9a8', heatmap_l2: '#40c463',
  heatmap_l3: '#30a14e', heatmap_l4: '#216e39',
};

const PRESETS: ThemePreset[] = [
  { id: 'default', name: 'Default', colors: { ...MOCK_THEME } },
  { id: 'ocean', name: 'Ocean', colors: { ...MOCK_THEME, primary: '#006994' } },
];

describe('ThemeEditor', () => {
  beforeEach(() => {
    vi.stubGlobal('adjustColor', undefined);
  });

  test('renders all 16 color inputs', () => {
    render(<ThemeEditor theme={MOCK_THEME} presets={PRESETS} onChange={() => {}} />);
    const colorInputs = screen.getAllByLabelText('color picker');
    expect(colorInputs.length).toBe(16);
  });

  test('renders preset cards', () => {
    render(<ThemeEditor theme={MOCK_THEME} presets={PRESETS} onChange={() => {}} />);
    expect(screen.getByText('Default')).toBeDefined();
    expect(screen.getByText('Ocean')).toBeDefined();
  });

  test('applies preset on click', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ThemeEditor theme={MOCK_THEME} presets={PRESETS} onChange={onChange} />);

    await user.click(screen.getByText('Ocean'));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ primary: '#006994' }));
  });

  test('calls onChange when a color input changes', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ThemeEditor theme={MOCK_THEME} presets={PRESETS} onChange={onChange} />);

    const hexInputs = screen.getAllByLabelText('hex value');
    const primaryHex = hexInputs[0] as HTMLInputElement;
    await user.clear(primaryHex);
    await user.type(primaryHex, '#FF0000');

    expect(onChange).toHaveBeenCalled();
  });

  test('resets to default preset on reset button click', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ThemeEditor theme={{ ...MOCK_THEME, primary: '#999999' }} presets={PRESETS} onChange={onChange} />);

    await user.click(screen.getByText(t('settings.theme.reset')));
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ primary: '#4f6d7a' }));
  });
});
