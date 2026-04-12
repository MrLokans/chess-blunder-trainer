import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/preact';

const { mockCg, mockChessground } = vi.hoisted(() => {
  const mockCg = {
    set: vi.fn(),
    setAutoShapes: vi.fn(),
    destroy: vi.fn(),
  };
  return { mockCg, mockChessground: vi.fn(() => mockCg) };
});

vi.mock('@vendor/chessground', () => ({
  Chessground: mockChessground,
}));

import { Board } from '../../src/trainer/components/Board';

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Board', () => {
  const defaultProps = {
    fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
    orientation: 'white' as const,
    interactive: true,
    coordinates: true,
    highlights: new Map<string, string>(),
    arrows: [] as Array<{ from: string; to: string; color: string }>,
    gameRef: { current: null },
    onMove: vi.fn(),
  };

  it('mounts Chessground with initial fen', () => {
    render(<Board {...defaultProps} />);
    expect(mockChessground).toHaveBeenCalledTimes(1);
    const config = mockChessground.mock.calls[0][1];
    expect(config.fen).toBe(defaultProps.fen);
    expect(config.orientation).toBe('white');
  });

  it('destroys Chessground on unmount', () => {
    const { unmount } = render(<Board {...defaultProps} />);
    unmount();
    expect(mockCg.destroy).toHaveBeenCalled();
  });

  it('syncs orientation changes', () => {
    const { rerender } = render(<Board {...defaultProps} />);
    rerender(<Board {...defaultProps} orientation="black" />);
    expect(mockCg.set).toHaveBeenCalledWith(expect.objectContaining({ orientation: 'black' }));
  });

  it('toggles hide-coords class', () => {
    const { container, rerender } = render(<Board {...defaultProps} coordinates={false} />);
    const board = container.querySelector('.cg-wrap');
    expect(board?.classList.contains('hide-coords')).toBe(true);
    rerender(<Board {...defaultProps} coordinates={true} />);
    expect(board?.classList.contains('hide-coords')).toBe(false);
  });
});
