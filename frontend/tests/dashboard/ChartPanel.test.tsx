import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { ChartPanel } from '../../src/dashboard/ChartPanel';

vi.stubGlobal('Chart', undefined);

describe('ChartPanel', () => {
  test('shows empty message when data is null', () => {
    render(
      <ChartPanel title="Chart" description="Desc" emptyMessage="No data" data={null} createChart={vi.fn()} />
    );
    expect(screen.getByText('No data')).toBeDefined();
  });

  test('shows empty message when data has no labels', () => {
    render(
      <ChartPanel title="Chart" description="Desc" emptyMessage="No data"
        data={{ labels: [], gameCounts: [], accuracies: [] }} createChart={vi.fn()} />
    );
    expect(screen.getByText('No data')).toBeDefined();
  });

  test('renders canvas when data exists', () => {
    const mockCreate = vi.fn().mockReturnValue({ destroy: vi.fn() });
    const { container } = render(
      <ChartPanel title="Chart" description="Desc" emptyMessage="No data"
        data={{ labels: ['Mon'], gameCounts: [5], accuracies: [80] }} createChart={mockCreate} />
    );
    expect(container.querySelector('canvas')).not.toBeNull();
  });
});
