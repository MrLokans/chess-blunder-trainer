import { Button } from '../components/primitives/Button';
import { StatCard } from '../components/data/StatCard';
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
        <span style="margin-left: var(--s-sm);">
          <Button variant="secondary" size="sm" onClick={onRetry}>
            {t('dashboard.analysis.retry')}
          </Button>
        </span>
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
      <StatCard label={t('dashboard.stat.total_games')} value={totalGames} />
      <StatCard label={t('dashboard.stat.analyzed_games')} value={analyzedGames} />
      <StatCard label={t('dashboard.stat.total_blunders')} value={totalBlunders} />
      <StatCard
        label={t('dashboard.stat.analysis_progress')}
        value={`${String(progressPercent)}%`}
      >
        <div class="progress-bar">
          <div class="progress-fill" style={{ width: `${String(progressPercent)}%` }} />
        </div>
        <AnalysisStatusDisplay status={analysisStatus} onRetry={onRetryAnalysis} />
      </StatCard>
    </div>
  );
}
