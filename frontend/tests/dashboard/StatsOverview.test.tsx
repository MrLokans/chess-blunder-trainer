import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { StatsOverview } from '../../src/dashboard/StatsOverview';

const props = {
  totalGames: 100,
  analyzedGames: 50,
  pendingAnalysis: 50,
  totalBlunders: 10,
  analysisStatus: { status: 'idle' as const },
  onRetryAnalysis: () => {},
};

describe('StatsOverview', () => {
  test('renders compact KPIs including API pending count', () => {
    render(<StatsOverview {...props} totalGames={150} analyzedGames={100} pendingAnalysis={50} totalBlunders={42} analysisStatus={{ status: 'completed' }} />);
    expect(screen.getByText('150')).toBeDefined();
    expect(screen.getByText('100')).toBeDefined();
    expect(screen.getByText('42')).toBeDefined();
    expect(screen.getByText(t('dashboard.stat.pending_analysis', { count: 50 }))).toBeDefined();
  });

  test('renders progress bar percentage', () => {
    const { container } = render(<StatsOverview {...props} totalGames={200} analyzedGames={100} pendingAnalysis={100} totalBlunders={0} />);
    expect(screen.getByText('50%')).toBeDefined();
    expect((container.querySelector('.progress-fill') as HTMLElement).style.width).toBe('50%');
  });

  test('shows running status with progress', () => {
    render(<StatsOverview {...props} analysisStatus={{ status: 'running', progress_current: 30, progress_total: 100 }} />);
    const statusEl = screen.getByTestId('analysis-status');
    expect(statusEl.textContent).not.toContain('{current}');
    expect(statusEl.textContent).not.toContain('{percent}');
    expect(statusEl.textContent).toContain('current=30');
    expect(statusEl.textContent).toContain('total=100');
    expect(statusEl.textContent).toContain('percent=30');
    expect(statusEl.className).toContain('dashboard-analysis-status--running');
  });

  test('shows completed status', () => {
    render(<StatsOverview {...props} analysisStatus={{ status: 'completed' }} />);
    expect(screen.getByTestId('analysis-status').className).toContain('dashboard-analysis-status--completed');
  });

  test('shows and hides retry button on failure', () => {
    const { rerender } = render(<StatsOverview {...props} analysisStatus={{ status: 'failed' }} />);
    expect(screen.getByText(t('dashboard.analysis.retry'))).toBeDefined();
    rerender(<StatsOverview {...props} analysisStatus={{ status: 'failed' }} showRetry={false} />);
    expect(screen.getByTestId('analysis-status').querySelector('button')).toBeNull();
  });
});
