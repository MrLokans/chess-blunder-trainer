import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { EngineControls } from '../../src/game-review/EngineControls';

const base = {
  analysisMode: true, multipv: 3, showArrows: true, showThreats: false, exploring: false,
  onToggleAnalysis: vi.fn(), onMultiPv: vi.fn(), onToggleArrows: vi.fn(),
  onToggleThreats: vi.fn(), onBackToGame: vi.fn(),
};

describe('EngineControls', () => {
  it('changes multipv via the selector', () => {
    const onMultiPv = vi.fn();
    render(<EngineControls {...base} onMultiPv={onMultiPv} />);
    fireEvent.change(screen.getByRole('combobox'), { target: { value: '5' } });
    expect(onMultiPv).toHaveBeenCalledWith(5);
  });

  it('shows the back-to-game control only while exploring', () => {
    const { rerender } = render(<EngineControls {...base} exploring={false} />);
    expect(screen.queryByRole('button', { name: 'game_review.engine.back_to_game' })).toBeNull();
    rerender(<EngineControls {...base} exploring={true} />);
    expect(screen.getByRole('button', { name: 'game_review.engine.back_to_game' })).toBeTruthy();
  });

  it('toggles arrows and threats', () => {
    const onToggleArrows = vi.fn();
    const onToggleThreats = vi.fn();
    render(<EngineControls {...base} onToggleArrows={onToggleArrows} onToggleThreats={onToggleThreats} />);
    fireEvent.click(screen.getByRole('checkbox', { name: 'game_review.engine.show_arrows' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'game_review.engine.show_threats' }));
    expect(onToggleArrows).toHaveBeenCalled();
    expect(onToggleThreats).toHaveBeenCalled();
  });
});
