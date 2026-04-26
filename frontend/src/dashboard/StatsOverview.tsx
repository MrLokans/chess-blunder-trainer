import type { AnalysisStatus } from './types';

export interface StatsOverviewProps {
  totalGames: number;
  analyzedGames: number;
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
    return (
      <div data-testid="analysis-status" class="text-sm text-muted mt-2 text-primary">
        {t('dashboard.analysis.running', { current, total, percent })}
      </div>
    );
  }

  if (status.status === 'completed') {
    return (
      <div data-testid="analysis-status" class="text-sm text-muted mt-2 text-success">
        {t('dashboard.analysis.completed')}
      </div>
    );
  }

  if (status.status === 'failed') {
    return (
      <div data-testid="analysis-status" class="text-sm text-muted mt-2 text-error">
        {t('dashboard.analysis.failed')}
        <button type="button" class="btn btn-sm" style="margin-left: 8px; padding: 4px 10px; font-size: 0.75rem;" onClick={onRetry}>
          {t('dashboard.analysis.retry')}
        </button>
      </div>
    );
  }

  return <div data-testid="analysis-status" class="text-sm text-muted mt-2" />;
}

export function StatsOverview({
  totalGames,
  analyzedGames,
  totalBlunders,
  analysisStatus,
  onRetryAnalysis,
}: StatsOverviewProps) {
  const progressPercent = totalGames > 0 ? Math.round((analyzedGames / totalGames) * 100) : 0;

  return (
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">{t('dashboard.stat.total_games')}</div>
        <div class="stat-value">{String(totalGames)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">{t('dashboard.stat.analyzed_games')}</div>
        <div class="stat-value">{String(analyzedGames)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">{t('dashboard.stat.total_blunders')}</div>
        <div class="stat-value">{String(totalBlunders)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">{t('dashboard.stat.analysis_progress')}</div>
        <div class="stat-value">{`${String(progressPercent)}%`}</div>
        <div class="progress-bar">
          <div class="progress-fill" style={{ width: `${String(progressPercent)}%` }} />
        </div>
        <AnalysisStatusDisplay status={analysisStatus} onRetry={onRetryAnalysis} />
      </div>
    </div>
  );
}
