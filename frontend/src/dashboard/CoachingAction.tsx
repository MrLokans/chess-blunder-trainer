import { useId } from 'preact/hooks';
import { Button, buttonClassName } from '../components/primitives/Button';
import { patternLabel } from './breakdowns';
import type { AnalysisStatus, GameBreakdownItem, PhaseData, TacticalData } from './types';

const MIN_PATTERN_OCCURRENCES = 5;

// Backend labels for blunders it could not attribute to a named tactic.
const UNNAMED_PATTERNS = new Set(['None', 'Unknown', 'Not Classified']);

const NAMED_PHASES = new Set(['opening', 'middlegame', 'endgame']);

const TRAINER_HREF = '/';
const MANAGEMENT_HREF = '/management';

export type NextActionKind =
  | 'no_games'
  | 'not_analyzed'
  | 'empty_filter'
  | 'analysis_failed'
  | 'analysis_pending'
  | 'train'
  | 'clean';

export type NextActionEvidence =
  | { kind: 'pattern'; pattern: string; count: number }
  | { kind: 'phase'; phase: string; count: number }
  | { kind: 'blunders'; count: number };

export interface NextActionInput {
  // Library-wide, unaffected by the dashboard filters. Importing and analyzing
  // are library operations, so they must not be judged from a filtered view.
  libraryGames: number;
  libraryAnalyzedGames: number;
  // Scoped to the active filters, like the rest of the dashboard.
  filteredGames: number;
  filteredBlunders: number;
  analysisStatus: AnalysisStatus['status'];
  tacticalData: TacticalData | null;
  phaseData: PhaseData | null;
}

export interface NextAction {
  kind: NextActionKind;
  pendingGames: number;
  evidence: NextActionEvidence | null;
}

function highestCount<T extends { count: number }>(entries: T[], nameOf: (entry: T) => string): T | null {
  return entries.reduce<T | null>((best, entry) => {
    if (best === null) return entry;
    if (entry.count !== best.count) return entry.count > best.count ? entry : best;
    return nameOf(entry) < nameOf(best) ? entry : best;
  }, null);
}

function patternEvidence(data: TacticalData | null): NextActionEvidence | null {
  if (!data) return null;
  const named = data.by_pattern.filter(
    p => !UNNAMED_PATTERNS.has(p.pattern) && p.count >= MIN_PATTERN_OCCURRENCES,
  );
  const top = highestCount(named, p => p.pattern);
  return top ? { kind: 'pattern', pattern: top.pattern, count: top.count } : null;
}

function phaseEvidence(data: PhaseData | null): NextActionEvidence | null {
  if (!data) return null;
  const named = data.by_phase.filter(p => NAMED_PHASES.has(p.phase) && p.count > 0);
  const top = highestCount(named, p => p.phase);
  return top ? { kind: 'phase', phase: top.phase, count: top.count } : null;
}

// The breakdown endpoint takes no filter params, so it is the only library-wide
// game count the dashboard already has on hand.
export function libraryTotals(gameBreakdown: GameBreakdownItem[] | null): Pick<NextActionInput, 'libraryGames' | 'libraryAnalyzedGames'> {
  const sources = gameBreakdown ?? [];
  return {
    libraryGames: sources.reduce((total, source) => total + source.total_games, 0),
    libraryAnalyzedGames: sources.reduce((total, source) => total + source.analyzed_games, 0),
  };
}

export function selectNextAction(input: NextActionInput): NextAction {
  const { libraryGames, libraryAnalyzedGames, filteredGames, filteredBlunders, analysisStatus } = input;
  const pendingGames = Math.max(libraryGames - libraryAnalyzedGames, 0);

  if (libraryGames <= 0) return { kind: 'no_games', pendingGames, evidence: null };
  if (libraryAnalyzedGames <= 0) return { kind: 'not_analyzed', pendingGames, evidence: null };
  if (filteredGames <= 0) return { kind: 'empty_filter', pendingGames, evidence: null };

  if (filteredBlunders <= 0) {
    if (analysisStatus === 'failed') return { kind: 'analysis_failed', pendingGames, evidence: null };
    if (analysisStatus === 'running' || pendingGames > 0) {
      return { kind: 'analysis_pending', pendingGames, evidence: null };
    }
    return { kind: 'clean', pendingGames, evidence: null };
  }

  const evidence =
    patternEvidence(input.tacticalData) ??
    phaseEvidence(input.phaseData) ??
    { kind: 'blunders' as const, count: filteredBlunders };

  return { kind: 'train', pendingGames, evidence };
}

interface CopyKeys {
  headline: string;
  body: string;
  cta: string;
}

// Spelled out rather than built from `kind` so `make lint/i18n` can verify
// each key exists in every locale instead of waving the prefix through.
const COPY_KEYS: Record<NextActionKind, CopyKeys> = {
  no_games: {
    headline: 'dashboard.coach.no_games.headline',
    body: 'dashboard.coach.no_games.body',
    cta: 'dashboard.coach.no_games.cta',
  },
  not_analyzed: {
    headline: 'dashboard.coach.not_analyzed.headline',
    body: 'dashboard.coach.not_analyzed.body',
    cta: 'dashboard.coach.not_analyzed.cta',
  },
  empty_filter: {
    headline: 'dashboard.coach.empty_filter.headline',
    body: 'dashboard.coach.empty_filter.body',
    cta: 'dashboard.coach.empty_filter.cta',
  },
  analysis_failed: {
    headline: 'dashboard.coach.analysis_failed.headline',
    body: 'dashboard.coach.analysis_failed.body',
    cta: 'dashboard.coach.analysis_failed.cta',
  },
  analysis_pending: {
    headline: 'dashboard.coach.analysis_pending.headline',
    body: 'dashboard.coach.analysis_pending.body',
    cta: 'dashboard.coach.analysis_pending.cta',
  },
  train: {
    headline: 'dashboard.coach.train.headline',
    body: 'dashboard.coach.train.body',
    cta: 'dashboard.coach.train.cta',
  },
  clean: {
    headline: 'dashboard.coach.clean.headline',
    body: 'dashboard.coach.clean.body',
    cta: 'dashboard.coach.clean.cta',
  },
};

// The two states that report how many games are still waiting.
const COUNTED_BODIES = new Set<NextActionKind>(['not_analyzed', 'analysis_pending']);

// The trainer queue ignores the dashboard filters, so it stays the useful
// action even when the filters select nothing.
const TRAINER_STATES = new Set<NextActionKind>(['train', 'empty_filter']);

function bodyText(action: NextAction): string {
  const key = COPY_KEYS[action.kind].body;
  return COUNTED_BODIES.has(action.kind) ? t(key, { count: action.pendingGames }) : t(key);
}

function evidenceLabel(evidence: NextActionEvidence): string {
  if (evidence.kind === 'pattern') return t('dashboard.coach.evidence.pattern');
  if (evidence.kind === 'phase') return t('dashboard.coach.evidence.phase');
  return t('dashboard.coach.evidence.overall');
}

function evidenceName(evidence: NextActionEvidence): string | null {
  if (evidence.kind === 'pattern') return patternLabel(evidence.pattern);
  if (evidence.kind === 'phase') return t(`chess.phase.${evidence.phase}`);
  return null;
}

export interface CoachingActionProps {
  action: NextAction;
  onRetryAnalysis: () => void;
}

export function CoachingAction({ action, onRetryAnalysis }: CoachingActionProps) {
  const headlineId = useId();
  const copy = COPY_KEYS[action.kind];
  const href = TRAINER_STATES.has(action.kind) ? TRAINER_HREF : MANAGEMENT_HREF;
  const evidence = action.evidence;
  const name = evidence ? evidenceName(evidence) : null;

  return (
    <section
      class="coach-card"
      data-testid="coaching-action"
      data-action={action.kind}
      aria-labelledby={headlineId}
    >
      <p class="coach-eyebrow">{t('dashboard.coach.title')}</p>
      <h2 id={headlineId} class="coach-headline">{t(copy.headline)}</h2>
      <p class="coach-body">{bodyText(action)}</p>

      {evidence && (
        <p class="coach-evidence">
          <span class="coach-evidence-label">{evidenceLabel(evidence)}</span>
          <span class="coach-evidence-value">
            {name && <strong class="coach-evidence-name">{name}</strong>}
            <span class="coach-evidence-count">
              {t('dashboard.coach.evidence.count', { count: evidence.count })}
            </span>
          </span>
        </p>
      )}

      <div class="coach-actions">
        {action.kind === 'analysis_failed' ? (
          <Button onClick={onRetryAnalysis}>{t(copy.cta)}</Button>
        ) : (
          <a class={buttonClassName('primary', 'md')} href={href}>{t(copy.cta)}</a>
        )}
      </div>

      {evidence && <p class="coach-note">{t('dashboard.coach.evidence.note')}</p>}
    </section>
  );
}
