import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { EvalBar } from '../../src/trainer/components/EvalBar';

describe('EvalBar', () => {
  it('renders with positive eval for white', () => {
    const { container } = render(<EvalBar cp={150} />);
    const fill = container.querySelector('.eval-bar-fill') as HTMLElement;
    const value = container.querySelector('.eval-value') as HTMLElement;
    expect(fill).not.toBeNull();
    expect(value).not.toBeNull();
    expect(value.textContent).toBe('+1.5');
  });

  it('renders with negative eval for white', () => {
    const { container } = render(<EvalBar cp={-200} />);
    const value = container.querySelector('.eval-value') as HTMLElement;
    expect(value.textContent).toBe('-2.0');
  });

  it('shows mate symbol for large eval', () => {
    const { container } = render(<EvalBar cp={10000} />);
    const value = container.querySelector('.eval-value') as HTMLElement;
    expect(value.textContent).toBe('+M');
  });

  it('clamps fill height between 0% and 100%', () => {
    const { container } = render(<EvalBar cp={9999} />);
    const fill = container.querySelector('.eval-bar-fill') as HTMLElement;
    expect(fill.style.height).toBe('100%');
  });

  it('renders 50% fill for equal position', () => {
    const { container } = render(<EvalBar cp={0} />);
    const fill = container.querySelector('.eval-bar-fill') as HTMLElement;
    expect(fill.style.height).toBe('50%');
  });

  it('fills above half when the player is better, whatever their colour', () => {
    // cp is player-perspective: puzzles store evals from the mover's side.
    const { container } = render(<EvalBar cp={200} />);
    const fill = container.querySelector('.eval-bar-fill') as HTMLElement;
    expect(parseFloat(fill.style.height)).toBeGreaterThan(50);
  });
});
