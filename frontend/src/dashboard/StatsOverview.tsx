import { Button } from '../components/primitives/Button';
import type { AnalysisStatus } from './types';

export interface StatsOverviewProps {
  totalGames: number;
  analyzedGames: number;
  pendingAnalysis: number;
  totalBlunders: number;
  analysisStatus: AnalysisStatus;
  onRetryAnalysis: () => void;
}

interface AnalysisStatusDisplayProps {
  status: AnalysisStatus;
  onRetry: () => void;
}

function AnalysisStatusDisplay({ status, onRetry }: AnalysisStatusDisplayProps) {
  if (status.status === 'running') {
    const current = status.progress_current ?? 0;
    const total = status.progress_total ?? 0;
    const percent = total > 0 ? Math.round((current / total) * 100) : 0;
    return <div data-testid="analysis-status" class="dashboard-analysis-status dashboard-analysis-status--running">{t('dashboard.analysis.running', { current, total, percent })}</div>;
  }
  if (status.status === 'completed') return <div data-testid="analysis-status" class="dashboard-analysis-status dashboard-analysis-status--completed">{t('dashboard.analysis.completed')}</div>;
  if (status.status === 'failed') {
    return <div data-testid="analysis-status" class="dashboard-analysis-status dashboard-analysis-status--failed">
      {t('dashboard.analysis.failed')}
      <span style="margin-left: var(--s-sm);"><Button variant="secondary" size="sm" onClick={onRetry}>{t('dashboard.analysis.retry')}</Button></span>
    </div>;
  }
  return <div data-testid="analysis-status" class="dashboard-analysis-status" />;
}

export function StatsOverview({
  totalGames,
  analyzedGames,
  pendingAnalysis,
  totalBlunders,
  analysisStatus,
  onRetryAnalysis,
}: StatsOverviewProps) {
  const progressPercent = totalGames > 0 ? Math.round((analyzedGames / totalGames) * 100) : 0;

  return (
    <div class="stats-grid dashboard-kpi-strip">
      <div class="dashboard-kpi"><span>{t('dashboard.stat.total_games')}</span><strong>{formatNumber(totalGames)}</strong></div>
      <div class="dashboard-kpi"><span>{t('dashboard.stat.analyzed_games')}</span><strong>{formatNumber(analyzedGames)}</strong><small>{t('dashboard.stat.pending_analysis', { count: pendingAnalysis })}</small></div>
      <div class="dashboard-kpi"><span>{t('dashboard.stat.total_blunders')}</span><strong>{formatNumber(totalBlunders)}</strong></div>
      <div class="dashboard-kpi dashboard-kpi--progress">
        <span>{t('dashboard.stat.analysis_progress')}</span><strong>{formatNumber(progressPercent)}%</strong>
        <div class="progress-bar"><div class="progress-fill" style={{ width: `${String(progressPercent)}%` }} /></div>
        <AnalysisStatusDisplay status={analysisStatus} onRetry={onRetryAnalysis} />
      </div>
    </div>
  );
}
