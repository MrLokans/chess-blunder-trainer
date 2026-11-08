import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { AccuracyChart, accuracyRange } from '../../src/dashboard/AccuracyChart';

describe('accuracyRange', () => {
  test('starts a little below the lowest accuracy, on a round ten', () => {
    expect(accuracyRange([82, 91])).toEqual({ low: 70, step: 10 });
    expect(accuracyRange([30, 90])).toEqual({ low: 20, step: 20 });
  });
});

describe('AccuracyChart', () => {
  test('shows the empty message when no slot has games', () => {
    render(<AccuracyChart title="T" description="D" emptyMessage="Nothing yet" data={{ labels: ['00:00'], gameCounts: [0], accuracies: [0] }} />);
    expect(screen.getByText('Nothing yet')).toBeDefined();
  });

  test('breaks the line where a slot has no games and leaves no dot there', () => {
    const { container } = render(
      <AccuracyChart
        title="T" description="D" emptyMessage="E"
        data={{ labels: ['a', 'b', 'c', 'd'], gameCounts: [3, 0, 4, 5], accuracies: [80, 0, 85, 90] }}
      />,
    );
    expect(container.querySelectorAll('polyline')).toHaveLength(2);
    expect(container.querySelectorAll('.accuracy-chart__dot')).toHaveLength(3);
    expect(container.querySelectorAll('.accuracy-chart__games > span')).toHaveLength(4);
  });

  test('lists every slot for screen readers', () => {
    const { container } = render(
      <AccuracyChart title="T" description="D" emptyMessage="E" data={{ labels: ['a', 'b'], gameCounts: [2, 0], accuracies: [88, 0] }} />,
    );
    const cells = Array.from(container.querySelectorAll('table tbody tr')).map(row => row.textContent);
    expect(cells).toEqual(['a88%2', 'b—0']);
  });
});
