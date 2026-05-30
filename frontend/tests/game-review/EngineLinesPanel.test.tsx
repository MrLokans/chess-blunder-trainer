import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { loadChessGlobal } from '../helpers/chess';
import { EngineLinesPanel } from '../../src/game-review/EngineLinesPanel';
import type { EngineLine } from '../../src/shared/engine/uci';

loadChessGlobal();

const startFen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const lines: EngineLine[] = [
  { multipv: 1, scoreCp: 30, mate: null, pv: ['e2e4', 'e7e5'] },
  { multipv: 2, scoreCp: 10, mate: null, pv: ['d2d4'] },
];

describe('EngineLinesPanel', () => {
  it('renders one row per line with SAN moves and eval', () => {
    render(<EngineLinesPanel fen={startFen} lines={lines} depth={18} onPlayLine={() => {}} />);
    expect(screen.getByText(/e4/)).toBeTruthy();
    expect(screen.getByText(/d4/)).toBeTruthy();
    expect(screen.getByText(/\+0\.3/)).toBeTruthy();
  });

  it('calls onPlayLine with the uci pv on row click', () => {
    const onPlay = vi.fn();
    render(<EngineLinesPanel fen={startFen} lines={lines} depth={18} onPlayLine={onPlay} />);
    fireEvent.click(screen.getByText(/e4/));
    expect(onPlay).toHaveBeenCalledWith(['e2e4', 'e7e5']);
  });

  it('renders mate scores with sign', () => {
    const mateLines: EngineLine[] = [
      { multipv: 1, scoreCp: null, mate: 3, pv: ['e2e4'] },
      { multipv: 2, scoreCp: null, mate: -2, pv: ['d2d4'] },
    ];
    render(<EngineLinesPanel fen={startFen} lines={mateLines} depth={20} onPlayLine={() => {}} />);
    expect(screen.getByText('#3')).toBeTruthy();
    expect(screen.getByText('#-2')).toBeTruthy();
  });

  it('renders only the header when lines is empty', () => {
    render(<EngineLinesPanel fen={startFen} lines={[]} depth={0} onPlayLine={() => {}} />);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('shows correct SAN for a Black-to-move position', () => {
    const blackFen = 'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1';
    const blackLines: EngineLine[] = [{ multipv: 1, scoreCp: -10, mate: null, pv: ['e7e5'] }];
    render(<EngineLinesPanel fen={blackFen} lines={blackLines} depth={12} onPlayLine={() => {}} />);
    expect(screen.getByText(/e5/)).toBeTruthy();
  });
});
