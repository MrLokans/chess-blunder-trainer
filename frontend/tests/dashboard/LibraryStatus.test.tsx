import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { LibraryStatus } from '../../src/dashboard/LibraryStatus';

const props = {
  totalGames: 100,
  analyzedGames: 50,
  pendingAnalysis: 50,
  totalBlunders: 10,
  analysisStatus: { status: 'idle' as const },
  onRetryAnalysis: () => {},
};

describe('LibraryStatus', () => {
  test('summarises the library in one line, pending count included', () => {
    render(<LibraryStatus {...props} totalGames={150} analyzedGames={100} pendingAnalysis={50} totalBlunders={42} />);
    const line = screen.getByTestId('library-status').textContent;
    expect(line).toContain(t('dashboard.status.games', { count: 150 }));
    expect(line).toContain(t('dashboard.status.analyzed', { count: 100 }));
    expect(line).toContain(t('dashboard.stat.pending_analysis', { count: 50 }));
    expect(line).toContain(t('dashboard.status.blunders', { count: 42 }));
  });

  test('omits the pending count once everything is analyzed', () => {
    render(<LibraryStatus {...props} pendingAnalysis={0} />);
    expect(screen.getByTestId('library-status').textContent).not.toContain(t('dashboard.stat.pending_analysis', { count: 0 }));
  });

  test('shows running status with progress', () => {
    render(<LibraryStatus {...props} analysisStatus={{ status: 'running', progress_current: 30, progress_total: 100 }} />);
    const statusEl = screen.getByTestId('analysis-status');
    expect(statusEl.textContent).toContain('current=30');
    expect(statusEl.textContent).toContain('total=100');
    expect(statusEl.textContent).toContain('percent=30');
    expect(statusEl.className).toContain('library-status__analysis--running');
  });

  test('shows and hides retry button on failure', () => {
    const { rerender } = render(<LibraryStatus {...props} analysisStatus={{ status: 'failed' }} />);
    expect(screen.getByText(t('dashboard.analysis.retry'))).toBeDefined();
    rerender(<LibraryStatus {...props} analysisStatus={{ status: 'failed' }} showRetry={false} />);
    expect(screen.getByTestId('analysis-status').querySelector('button')).toBeNull();
  });
});
