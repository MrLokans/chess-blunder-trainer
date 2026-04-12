import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { ProgressBar } from '../../src/components/ProgressBar';

describe('ProgressBar', () => {
  test('displays progress text', () => {
    render(<ProgressBar current={30} total={100} />);
    expect(screen.getByText('30/100 (30%)')).toBeDefined();
  });

  test('sets fill width to percentage', () => {
    const { container } = render(<ProgressBar current={75} total={100} />);
    const fill = container.querySelector('.progress-fill') as HTMLElement;
    expect(fill.style.width).toBe('75%');
  });

  test('handles zero total without division error', () => {
    render(<ProgressBar current={0} total={0} />);
    expect(screen.getByText('0/0 (0%)')).toBeDefined();
  });

  test('supports custom text format', () => {
    const fmt = (current: number, total: number) => `${String(current)} of ${String(total)} games`;
    render(<ProgressBar current={5} total={20} textFormat={fmt} />);
    expect(screen.getByText('5 of 20 games')).toBeDefined();
  });

  test('updates when props change', () => {
    const { rerender } = render(<ProgressBar current={10} total={100} />);
    expect(screen.getByText('10/100 (10%)')).toBeDefined();

    rerender(<ProgressBar current={50} total={100} />);
    expect(screen.getByText('50/100 (50%)')).toBeDefined();
  });
});
