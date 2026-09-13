import { describe, test, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/preact';
import { CoachingAction, libraryTotals, selectNextAction } from '../../src/dashboard/CoachingAction';
import type { NextActionInput, NextActionKind } from '../../src/dashboard/CoachingAction';
import type { GameBreakdownItem, PhaseData, TacticalData } from '../../src/dashboard/types';

function tactical(entries: Array<[string, number]>): TacticalData {
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return {
    total_blunders: total,
    by_pattern: entries.map(([pattern, count]) => ({
      pattern,
      count,
      percentage: total > 0 ? Math.round((count / total) * 100) : 0,
    })),
  };
}

function phases(entries: Array<[string, number]>): PhaseData {
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  return {
    total_blunders: total,
    by_phase: entries.map(([phase, count]) => ({
      phase,
      count,
      percentage: total > 0 ? Math.round((count / total) * 100) : 0,
      avg_cp_loss: 300,
    })),
  };
}

function input(overrides: Partial<NextActionInput> = {}): NextActionInput {
  return {
    libraryGames: 100,
    libraryAnalyzedGames: 100,
    filteredGames: 100,
    filteredBlunders: 0,
    analysisStatus: 'completed',
    tacticalData: null,
    phaseData: null,
    ...overrides,
  };
}

function breakdown(totalGames: number, analyzedGames: number): GameBreakdownItem[] {
  return [
    {
      source: 'lichess',
      username: 'player',
      total_games: totalGames,
      analyzed_games: analyzedGames,
      pending_games: Math.max(totalGames - analyzedGames, 0),
    },
  ];
}

describe('libraryTotals', () => {
  test('treats a missing breakdown as an empty library', () => {
    expect(libraryTotals(null)).toEqual({ libraryGames: 0, libraryAnalyzedGames: 0 });
  });

  test('sums every source', () => {
    expect(libraryTotals([...breakdown(10, 8), ...breakdown(5, 5)]))
      .toEqual({ libraryGames: 15, libraryAnalyzedGames: 13 });
  });
});

describe('selectNextAction', () => {
  const cases: Array<[string, Partial<NextActionInput>, NextActionKind]> = [
    ['no games imported', { libraryGames: 0, libraryAnalyzedGames: 0, filteredGames: 0 }, 'no_games'],
    ['games imported, none analyzed', { libraryGames: 40, libraryAnalyzedGames: 0, filteredGames: 40 }, 'not_analyzed'],
    ['nothing analyzed after a failed run', { libraryGames: 40, libraryAnalyzedGames: 0, filteredGames: 40, analysisStatus: 'failed' }, 'not_analyzed'],
    ['filters select nothing', { filteredGames: 0 }, 'empty_filter'],
    ['filters select nothing despite library blunders', { filteredGames: 0, filteredBlunders: 0 }, 'empty_filter'],
    ['failed run, no blunders', { analysisStatus: 'failed' }, 'analysis_failed'],
    ['running, no blunders', { analysisStatus: 'running' }, 'analysis_pending'],
    ['idle with unanalyzed games, no blunders', { libraryGames: 100, libraryAnalyzedGames: 60 }, 'analysis_pending'],
    ['blunders present', { filteredBlunders: 12 }, 'train'],
    ['blunders present while analysis still running', { filteredBlunders: 12, analysisStatus: 'running' }, 'train'],
    ['blunders present after a failed run', { filteredBlunders: 12, analysisStatus: 'failed' }, 'train'],
    ['fully analyzed, no blunders', {}, 'clean'],
  ];

  test.each(cases)('%s -> %s', (_name, overrides, expected) => {
    expect(selectNextAction(input(overrides)).kind).toBe(expected);
  });

  test('is deterministic for identical input', () => {
    const args = input({ filteredBlunders: 30, tacticalData: tactical([['Fork', 9], ['Pin', 9]]) });
    expect(selectNextAction(args)).toEqual(selectNextAction(args));
  });

  test('counts games awaiting analysis across the whole library, not the filtered view', () => {
    const action = selectNextAction(input({
      libraryGames: 100,
      libraryAnalyzedGames: 60,
      filteredGames: 10,
    }));
    expect(action.pendingGames).toBe(40);
  });

  test('never reports negative pending games', () => {
    expect(selectNextAction(input({ libraryGames: 10, libraryAnalyzedGames: 25 })).pendingGames).toBe(0);
  });

  test('does not mistake an empty filter for an empty library', () => {
    const action = selectNextAction(input({
      libraryGames: 727,
      libraryAnalyzedGames: 727,
      filteredGames: 0,
    }));
    expect(action.kind).toBe('empty_filter');
  });

  describe('evidence', () => {
    test('prefers the highest-count named pattern', () => {
      const action = selectNextAction(input({
        filteredBlunders: 30,
        tacticalData: tactical([['Fork', 12], ['Pin', 7]]),
        phaseData: phases([['middlegame', 20]]),
      }));
      expect(action.evidence).toEqual({ kind: 'pattern', pattern: 'Fork', count: 12 });
    });

    test('ignores unclassified patterns however common', () => {
      const action = selectNextAction(input({
        filteredBlunders: 30,
        tacticalData: tactical([['Not Classified', 40], ['None', 30], ['Unknown', 20], ['Pin', 6]]),
      }));
      expect(action.evidence).toEqual({ kind: 'pattern', pattern: 'Pin', count: 6 });
    });

    test('ignores patterns below the occurrence threshold', () => {
      const action = selectNextAction(input({
        filteredBlunders: 8,
        tacticalData: tactical([['Fork', 4]]),
        phaseData: phases([['endgame', 8]]),
      }));
      expect(action.evidence).toEqual({ kind: 'phase', phase: 'endgame', count: 8 });
    });

    test('breaks pattern ties by name', () => {
      const forkFirst = selectNextAction(input({ filteredBlunders: 18, tacticalData: tactical([['Fork', 9], ['Pin', 9]]) }));
      const pinFirst = selectNextAction(input({ filteredBlunders: 18, tacticalData: tactical([['Pin', 9], ['Fork', 9]]) }));
      expect(forkFirst.evidence).toEqual({ kind: 'pattern', pattern: 'Fork', count: 9 });
      expect(pinFirst.evidence).toEqual(forkFirst.evidence);
    });

    test('breaks phase ties by name', () => {
      const action = selectNextAction(input({
        filteredBlunders: 20,
        phaseData: phases([['opening', 10], ['endgame', 10]]),
      }));
      expect(action.evidence).toEqual({ kind: 'phase', phase: 'endgame', count: 10 });
    });

    test('skips empty phases', () => {
      const action = selectNextAction(input({
        filteredBlunders: 5,
        phaseData: phases([['opening', 0], ['middlegame', 5], ['endgame', 0]]),
      }));
      expect(action.evidence).toEqual({ kind: 'phase', phase: 'middlegame', count: 5 });
    });

    test('falls back to the blunder total when both breakdowns are disabled', () => {
      const action = selectNextAction(input({ filteredBlunders: 17, tacticalData: null, phaseData: null }));
      expect(action.evidence).toEqual({ kind: 'blunders', count: 17 });
    });

    test('falls back to the blunder total when both breakdowns are empty', () => {
      const action = selectNextAction(input({
        filteredBlunders: 17,
        tacticalData: tactical([]),
        phaseData: phases([]),
      }));
      expect(action.evidence).toEqual({ kind: 'blunders', count: 17 });
    });

    test('is omitted for every non-training state', () => {
      const kinds: Array<Partial<NextActionInput>> = [
        { libraryGames: 0, libraryAnalyzedGames: 0, filteredGames: 0 },
        { libraryGames: 40, libraryAnalyzedGames: 0 },
        { filteredGames: 0 },
        { analysisStatus: 'failed' },
        { analysisStatus: 'running' },
        {},
      ];
      for (const overrides of kinds) {
        expect(selectNextAction(input(overrides)).evidence).toBeNull();
      }
    });
  });
});

function renderCard(overrides: Partial<NextActionInput> = {}, onRetry = () => {}) {
  return render(
    <CoachingAction action={selectNextAction(input(overrides))} onRetryAnalysis={onRetry} />,
  );
}

describe('CoachingAction', () => {
  test('renders exactly one primary action per state', () => {
    const states: Array<Partial<NextActionInput>> = [
      { libraryGames: 0, libraryAnalyzedGames: 0, filteredGames: 0 },
      { libraryGames: 40, libraryAnalyzedGames: 0 },
      { filteredGames: 0 },
      { analysisStatus: 'failed' },
      { analysisStatus: 'running' },
      { filteredBlunders: 12 },
      {},
    ];
    for (const overrides of states) {
      const { container, unmount } = renderCard(overrides);
      expect(container.querySelectorAll('.coach-actions .btn')).toHaveLength(1);
      unmount();
    }
  });

  test('sends the training state to the trainer without claiming a filtered queue', () => {
    renderCard({ filteredBlunders: 12, tacticalData: tactical([['Fork', 12]]) });
    const cta = screen.getByText(t('dashboard.coach.train.cta'));
    expect(cta.getAttribute('href')).toBe('/');
    expect(screen.getByTestId('coaching-action').textContent).toContain(t('dashboard.coach.train.body'));
  });

  test('sends the import and analysis states to management', () => {
    const states: Array<Partial<NextActionInput>> = [
      { libraryGames: 0, libraryAnalyzedGames: 0, filteredGames: 0 },
      { libraryGames: 40, libraryAnalyzedGames: 0 },
      { analysisStatus: 'running' },
      {},
    ];
    for (const overrides of states) {
      const { container, unmount } = renderCard(overrides);
      expect(container.querySelector('.coach-actions a')?.getAttribute('href')).toBe('/management');
      unmount();
    }
  });

  test('keeps the trainer reachable when the filters select nothing', () => {
    const { container } = renderCard({ filteredGames: 0 });
    expect(screen.getByText(t('dashboard.coach.empty_filter.headline'))).toBeDefined();
    expect(container.querySelector('.coach-actions a')?.getAttribute('href')).toBe('/');
  });



  test('retries analysis in place instead of navigating', () => {
    const onRetry = vi.fn();
    const { container } = renderCard({ analysisStatus: 'failed' }, onRetry);
    expect(container.querySelector('.coach-actions a')).toBeNull();
    fireEvent.click(screen.getByText(t('dashboard.coach.analysis_failed.cta')));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  test('passes the pending count to the analysis copy', () => {
    renderCard({ libraryGames: 100, libraryAnalyzedGames: 60 });
    const text = screen.getByTestId('coaching-action').textContent;
    expect(text).toContain(t('dashboard.coach.analysis_pending.body', { count: 40 }));
    expect(text).not.toContain('{count}');
  });

  test('names the pattern behind the training recommendation', () => {
    renderCard({ filteredBlunders: 30, tacticalData: tactical([['Fork', 12], ['Pin', 7]]) });
    expect(screen.getByText(t('dashboard.tactical.fork'))).toBeDefined();
    expect(screen.getByText(t('dashboard.coach.evidence.pattern'))).toBeDefined();
    expect(screen.getByText(t('dashboard.coach.evidence.count', { count: 12 }))).toBeDefined();
  });

  test('names the phase when the tactical breakdown is disabled', () => {
    renderCard({ filteredBlunders: 20, tacticalData: null, phaseData: phases([['middlegame', 14], ['opening', 6]]) });
    expect(screen.getByText(t('chess.phase.middlegame'))).toBeDefined();
    expect(screen.getByText(t('dashboard.coach.evidence.phase'))).toBeDefined();
  });

  test('shows the blunder total when both breakdowns are disabled', () => {
    const { container } = renderCard({ filteredBlunders: 17, tacticalData: null, phaseData: null });
    expect(screen.getByText(t('dashboard.coach.evidence.overall'))).toBeDefined();
    expect(screen.getByText(t('dashboard.coach.evidence.count', { count: 17 }))).toBeDefined();
    expect(container.querySelector('.coach-evidence-name')).toBeNull();
  });

  test('qualifies the evidence as raw volume', () => {
    renderCard({ filteredBlunders: 30, tacticalData: tactical([['Fork', 12]]) });
    expect(screen.getByText(t('dashboard.coach.evidence.note'))).toBeDefined();
  });

  test('omits the evidence row outside the training state', () => {
    const { container } = renderCard({});
    expect(container.querySelector('.coach-evidence')).toBeNull();
    expect(container.querySelector('.coach-note')).toBeNull();
  });

  test('labels the card by its headline', () => {
    const { container } = renderCard({ filteredBlunders: 12 });
    const card = screen.getByTestId('coaching-action');
    const headlineId = card.getAttribute('aria-labelledby');
    expect(container.querySelector(`#${String(headlineId)}`)?.textContent)
      .toBe(t('dashboard.coach.train.headline'));
  });
});
