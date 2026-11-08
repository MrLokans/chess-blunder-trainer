import { Button } from '../components/primitives/Button';
import type { AnalysisStatus } from './types';

export interface LibraryStatusProps {
  totalGames: number;
  analyzedGames: number;
  pendingAnalysis: number;
  totalBlunders: number;
  analysisStatus: AnalysisStatus;
  onRetryAnalysis: () => void;
  showRetry?: boolean;
}

function AnalysisState({ status, onRetry, showRetry }: { status: AnalysisStatus; onRetry: () => void; showRetry: boolean }) {
  if (status.status === 'running') {
    const current = status.progress_current ?? 0;
    const total = status.progress_total ?? 0;
    const percent = total > 0 ? Math.round((current / total) * 100) : 0;
    return <span data-testid="analysis-status" class="library-status__analysis library-status__analysis--running">{t('dashboard.analysis.running', { current, total, percent })}</span>;
  }
  if (status.status === 'completed') return <span data-testid="analysis-status" class="library-status__analysis">{t('dashboard.analysis.completed')}</span>;
  if (status.status === 'failed') {
    return (
      <span data-testid="analysis-status" class="library-status__analysis library-status__analysis--failed">
        {t('dashboard.analysis.failed')}
        {showRetry && <Button variant="secondary" size="sm" onClick={onRetry}>{t('dashboard.analysis.retry')}</Button>}
      </span>
    );
  }
  return null;
}

export function LibraryStatus({
  totalGames,
  analyzedGames,
  pendingAnalysis,
  totalBlunders,
  analysisStatus,
  onRetryAnalysis,
  showRetry = true,
}: LibraryStatusProps) {
  return (
    <p class="library-status" data-testid="library-status">
      <span>{t('dashboard.status.games', { count: totalGames })}</span>
      <span>{t('dashboard.status.analyzed', { count: analyzedGames })}</span>
      {pendingAnalysis > 0 && <span>{t('dashboard.stat.pending_analysis', { count: pendingAnalysis })}</span>}
      <span>{t('dashboard.status.blunders', { count: totalBlunders })}</span>
      <AnalysisState status={analysisStatus} onRetry={onRetryAnalysis} showRetry={showRetry} />
    </p>
  );
}
