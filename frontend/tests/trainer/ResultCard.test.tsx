import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { ResultCard } from '../../src/trainer/components/ResultCard';

const puzzle = {
  game_id: 'abc', fen: 'startpos', ply: 10,
  blunder_uci: 'e2e4', blunder_san: 'e4',
  best_move_uci: 'd2d4', best_move_san: 'd4',
  best_line: ['d4', 'Nf6', 'c4'], player_color: 'white' as const,
  eval_before: 50, eval_after: -200,
  eval_before_display: '+0.5', eval_after_display: '-2.0',
  cp_loss: 250, game_phase: 'middlegame',
  tactical_pattern: 'fork', tactical_reason: 'Knight forks king and rook',
  tactical_squares: ['e5'], explanation_blunder: 'Loses material',
  explanation_best: 'Maintains advantage', game_url: null,
  difficulty: 'medium', pre_move_uci: null, pre_move_fen: null,
  best_move_eval: 60,
};

describe('ResultCard', () => {
  const defaults = {
    visible: true,
    feedbackType: 'correct' as const,
    feedbackTitle: 'Excellent!',
    feedbackDetail: 'You found the best move',
    puzzle,
    bestRevealed: true,
    moveHistory: [] as string[],
    onPlayBest: vi.fn(),
    onNext: vi.fn(),
    onClose: vi.fn(),
  };

  it('renders when visible', () => {
    render(<ResultCard {...defaults} />);
    expect(screen.getByText('Excellent!')).not.toBeNull();
    expect(screen.getByText('You found the best move')).not.toBeNull();
  });

  it('does not render when not visible', () => {
    const { container } = render(<ResultCard {...defaults} visible={false} />);
    expect(container.querySelector('.board-result-card')).toBeNull();
  });

  it('shows best move when revealed', () => {
    render(<ResultCard {...defaults} />);
    expect(screen.getByRole('button', { name: 'd4' })).not.toBeNull();
    expect(screen.getByRole('button', { name: 'Nf6' })).not.toBeNull();
    expect(screen.getByRole('button', { name: 'c4' })).not.toBeNull();
  });

  it('shows tactical details', () => {
    render(<ResultCard {...defaults} />);
    expect(screen.getByText('fork')).not.toBeNull();
  });

  it('calls onNext on next button click', () => {
    render(<ResultCard {...defaults} />);
    const nextBtn = screen.getByText('trainer.shortcuts.next', { exact: false });
    fireEvent.click(nextBtn);
    expect(defaults.onNext).toHaveBeenCalled();
  });

  it('hides play best button for correct feedback', () => {
    render(<ResultCard {...defaults} feedbackType="correct" />);
    expect(screen.queryByText('trainer.button.play_best', { exact: false })).toBeNull();
  });

  it('shows play best button for non-correct feedback', () => {
    render(<ResultCard {...defaults} feedbackType="blunder" />);
    expect(screen.getByText('trainer.button.play_best', { exact: false })).not.toBeNull();
  });
});
