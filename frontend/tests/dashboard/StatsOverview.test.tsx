import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { StatsOverview } from '../../src/dashboard/StatsOverview';

describe('StatsOverview', () => {
  test('renders stat values', () => {
    render(
      <StatsOverview
        totalGames={150}
        analyzedGames={100}
        totalBlunders={42}
        analysisStatus={{ status: 'completed' }}
        onRetryAnalysis={() => {}}
      />
    );
    expect(screen.getByText('150')).toBeDefined();
    expect(screen.getByText('100')).toBeDefined();
    expect(screen.getByText('42')).toBeDefined();
  });

  test('renders progress bar percentage', () => {
    const { container } = render(
      <StatsOverview
        totalGames={200}
        analyzedGames={100}
        totalBlunders={0}
        analysisStatus={{ status: 'idle' }}
        onRetryAnalysis={() => {}}
      />
    );
    expect(screen.getByText('50%')).toBeDefined();
    const fill = container.querySelector('.progress-fill') as HTMLElement;
    expect(fill.style.width).toBe('50%');
  });

  test('shows running status with progress', () => {
    render(
      <StatsOverview
        totalGames={100}
        analyzedGames={50}
        totalBlunders={10}
        analysisStatus={{ status: 'running', progress_current: 30, progress_total: 100 }}
        onRetryAnalysis={() => {}}
      />
    );
    const statusEl = screen.getByTestId('analysis-status');
    expect(statusEl.textContent).toContain('30');
    expect(statusEl.className).toContain('text-primary');
  });

  test('shows completed status', () => {
    render(
      <StatsOverview
        totalGames={100}
        analyzedGames={100}
        totalBlunders={10}
        analysisStatus={{ status: 'completed' }}
        onRetryAnalysis={() => {}}
      />
    );
    const statusEl = screen.getByTestId('analysis-status');
    expect(statusEl.className).toContain('text-success');
  });

  test('shows retry button on failure', () => {
    render(
      <StatsOverview
        totalGames={100}
        analyzedGames={50}
        totalBlunders={10}
        analysisStatus={{ status: 'failed' }}
        onRetryAnalysis={() => {}}
      />
    );
    expect(screen.getByText(t('dashboard.analysis.retry'))).toBeDefined();
  });
});
