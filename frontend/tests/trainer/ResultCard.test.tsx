import { beforeEach, describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { ResultCard } from '../../src/trainer/components/ResultCard';
import { loadChessGlobal } from '../helpers/chess';

const { mockChessground } = vi.hoisted(() => ({
  mockChessground: vi.fn(() => ({ set: vi.fn(), setAutoShapes: vi.fn(), destroy: vi.fn() })),
}));

vi.mock('@vendor/chessground', () => ({ Chessground: mockChessground }));

const puzzle = {
  game_id: 'abc', fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1', ply: 10,
  blunder_uci: 'e2e4', blunder_san: 'e4',
  best_move_uci: 'd2d4', best_move_san: 'd4',
  best_line: ['d4', 'Nf6', 'c4'], refutation_line: ['Nf6', 'Nc3', 'Bb4'], player_color: 'white' as const,
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
  beforeEach(() => { loadChessGlobal(); });

  const defaults = {
    visible: true,
    feedbackType: 'correct' as const,
    feedbackTitle: 'Excellent!',
    feedbackDetail: 'You found the best move',
    puzzle,
    bestRevealed: true,
    userAttempt: null,
    moveHistory: [] as string[],
    onPlayBest: vi.fn(),
    onPlayRefutation: vi.fn(),
    onNext: vi.fn(),
  };

  it('renders when visible', () => {
    render(<ResultCard {...defaults} />);
    expect(screen.getByText('Excellent!')).not.toBeNull();
    expect(screen.getByText('You found the best move')).not.toBeNull();
  });

  it('does not render when not visible', () => {
    const { container } = render(<ResultCard {...defaults} visible={false} />);
    expect(container.querySelector('#boardResultCard')).toBeNull();
  });

  it('shows best move when revealed', () => {
    render(<ResultCard {...defaults} />);
    expect(screen.getByText('d4')).not.toBeNull();
    expect(screen.getByText('Nf6 c4')).not.toBeNull();
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

  it('shows play line button for correct feedback', () => {
    render(<ResultCard {...defaults} feedbackType="correct" />);
    expect(screen.getByText('trainer.button.play_line', { exact: false })).not.toBeNull();
  });

  it('calls onPlayBest when the play line button is clicked', () => {
    const onPlayBest = vi.fn();
    render(<ResultCard {...defaults} feedbackType="correct" onPlayBest={onPlayBest} />);
    fireEvent.click(screen.getByText('trainer.button.play_line', { exact: false }));
    expect(onPlayBest).toHaveBeenCalled();
  });

  it('shows play best button for non-correct feedback', () => {
    render(<ResultCard {...defaults} feedbackType="blunder" />);
    expect(screen.getByText('trainer.button.play_best', { exact: false })).not.toBeNull();
  });

  it('shows the refutation of the played move', () => {
    const { getByTestId } = render(<ResultCard {...defaults} />);
    expect(getByTestId('result-blunder').textContent).toContain('trainer.result.you_played');
    expect(getByTestId('refutation-line').textContent).toBe('Nf6 Nc3 Bb4');
    expect(screen.getByText('Loses material')).not.toBeNull();
  });

  it('calls onPlayRefutation when show refutation is clicked', () => {
    const onPlayRefutation = vi.fn();
    const { getByTestId } = render(<ResultCard {...defaults} onPlayRefutation={onPlayRefutation} />);
    fireEvent.click(getByTestId('show-refutation'));
    expect(onPlayRefutation).toHaveBeenCalled();
  });

  it('omits the refutation button when there is no refutation line', () => {
    const { queryByTestId, getByTestId } = render(
      <ResultCard {...defaults} puzzle={{ ...puzzle, refutation_line: [] }} />,
    );
    expect(queryByTestId('show-refutation')).toBeNull();
    expect(getByTestId('result-blunder')).not.toBeNull();
  });

  it('explains why the best move is better', () => {
    const { getByTestId } = render(<ResultCard {...defaults} />);
    expect(getByTestId('result-best').textContent).toContain('Maintains advantage');
  });

  it('compares the attempted move with the best move on two boards', () => {
    mockChessground.mockClear();
    render(<ResultCard {...defaults} feedbackType="not-quite" userAttempt={{ san: 'Nf3', uci: 'g1f3', evalDisplay: '+0.2' }} />);
    expect(screen.getByText('trainer.result.your_move')).not.toBeNull();
    expect(screen.getAllByRole('img')).toHaveLength(2);
    expect(mockChessground).toHaveBeenCalledTimes(2);
    expect(mockChessground.mock.calls.map(([, cfg]) => (cfg as { lastMove: string[] }).lastMove)).toEqual([['g1', 'f3'], ['d2', 'd4']]);
  });

  it('falls back to the game move when the answer was only revealed', () => {
    render(<ResultCard {...defaults} feedbackType={null} />);
    expect(screen.getByText('trainer.result.in_game')).not.toBeNull();
  });

  it('shows only the best board when the move was correct', () => {
    mockChessground.mockClear();
    render(<ResultCard {...defaults} />);
    expect(screen.queryByText('trainer.result.your_move')).toBeNull();
    expect(mockChessground).toHaveBeenCalledTimes(1);
  });

  it('skips a board whose move is illegal in the puzzle position', () => {
    mockChessground.mockClear();
    render(<ResultCard {...defaults} feedbackType="not-quite" userAttempt={{ san: 'Ke2', uci: 'e1e2', evalDisplay: '-9' }} />);
    expect(screen.queryByText('trainer.result.your_move')).toBeNull();
    expect(mockChessground).toHaveBeenCalledTimes(1);
  });
});
