import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { RankedBars, leaderKey } from '../../src/dashboard/RankedBars';
import type { RankedBar } from '../../src/dashboard/RankedBars';

const row = (key: string, value: number, extra: Partial<RankedBar> = {}): RankedBar => ({ key, label: key, value, display: String(value), ...extra });

describe('leaderKey', () => {
  test('picks a clear leader', () => {
    expect(leaderKey([row('a', 5), row('b', 10)])).toBe('b');
  });

  test('picks nobody on a tie or a near tie', () => {
    expect(leaderKey([row('a', 1), row('b', 1)])).toBeNull();
    expect(leaderKey([row('a', 0.95), row('b', 0.94)])).toBeNull();
  });

  test('ignores muted rows and all-zero values', () => {
    expect(leaderKey([row('other', 60, { muted: true }), row('fork', 10), row('pin', 2)])).toBe('fork');
    expect(leaderKey([row('a', 0), row('b', 0)])).toBeNull();
  });
});

describe('RankedBars', () => {
  test('still lists rows when every value is zero', () => {
    const { container } = render(<RankedBars rows={[row('a', 0), row('b', 0)]} />);
    expect(container.querySelectorAll('tbody tr')).toHaveLength(2);
  });

  test('scales bars to a fixed top when given one', () => {
    const { container } = render(<RankedBars scale={100} rows={[row('a', 50)]} />);
    expect((container.querySelector('.ranked-bars__bar') as HTMLElement).style.width).toBe('50%');
  });

  test('can turn the highlight off', () => {
    const { container } = render(<RankedBars highlight={false} rows={[row('a', 5), row('b', 50)]} />);
    expect(container.querySelector('.ranked-bars__row--top')).toBeNull();
  });
});
