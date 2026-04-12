import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { VimInput } from '../../src/trainer/components/VimInput';
import { loadChessGlobal } from '../helpers/chess';

beforeEach(() => {
  loadChessGlobal();
  vi.clearAllMocks();
});

describe('VimInput', () => {
  const defaultProps = {
    visible: true,
    game: null as ChessInstance | null,
    interactive: true,
    onMove: vi.fn(),
    onClose: vi.fn(),
  };

  it('renders when visible', () => {
    const { container } = render(<VimInput {...defaultProps} />);
    expect(container.querySelector('.vim-input-overlay')).not.toBeNull();
  });

  it('does not render when not visible', () => {
    const { container } = render(<VimInput {...defaultProps} visible={false} />);
    expect(container.querySelector('.vim-input-overlay')).toBeNull();
  });

  it('shows suggestions on input', () => {
    const game = new Chess();
    render(<VimInput {...defaultProps} game={game} />);
    const input = screen.getByRole('textbox');
    fireEvent.input(input, { target: { value: 'e' } });
    const suggestions = document.querySelectorAll('.vim-suggestion');
    expect(suggestions.length).toBeGreaterThan(0);
  });

  it('closes on Escape', () => {
    render(<VimInput {...defaultProps} />);
    const input = screen.getByRole('textbox');
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('executes move on Enter', () => {
    const game = new Chess();
    render(<VimInput {...defaultProps} game={game} />);
    const input = screen.getByRole('textbox');
    fireEvent.input(input, { target: { value: 'e4' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    expect(defaultProps.onMove).toHaveBeenCalledWith(
      expect.objectContaining({ san: 'e4', from: 'e2', to: 'e4' }),
    );
  });
});
