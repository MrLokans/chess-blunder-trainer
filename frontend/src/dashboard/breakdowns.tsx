import { useState } from 'preact/hooks';
import { groupOpeningsByBase, openingNameSlug } from '../shared/opening-group';
import { DataTable } from '../components/data/DataTable';
import type { Column } from '../components/data/DataTable';
import type { OpeningItem } from '../shared/opening-group';
import type {
  PhaseData,
  ColorData,
  GameTypeData,
  EcoData,
  TacticalData,
  DifficultyData,
  CollapsePointData,
  ConversionResilienceData,
} from './types';
import type { TrapStatsResponse } from '../types/api';
import { RankedBars } from './RankedBars';
import { UNNAMED_PATTERNS } from './patterns';

export function renderOpeningName(ecoCode: string, ecoName: string): import('preact').JSX.Element {
  const colonIdx = ecoName.indexOf(': ');
  const lichessUrl = `https://lichess.org/opening/${openingNameSlug(ecoName)}`;
  const ecoUrl = `https://www.365chess.com/eco/${ecoCode}`;

  let nameJsx: import('preact').JSX.Element;
  if (colonIdx > -1) {
    const base = ecoName.substring(0, colonIdx);
    const variation = ecoName.substring(colonIdx + 2);
    const commaIdx = variation.indexOf(', ');
    if (commaIdx > -1) {
      nameJsx = (
        <>
          <span class="eco-name-base">{base}</span>:{' '}
          <span class="eco-name-variation">{variation.substring(0, commaIdx)}</span>,{' '}
          <span class="eco-name-subvariation">{variation.substring(commaIdx + 2)}</span>
        </>
      );
    } else {
      nameJsx = (
        <>
          <span class="eco-name-base">{base}</span>:{' '}
          <span class="eco-name-variation">{variation}</span>
        </>
      );
    }
  } else {
    nameJsx = <span class="eco-name-base">{ecoName}</span>;
  }

  return (
    <>
      <a href={ecoUrl} target="_blank" rel="noopener" class="eco-code" title={ecoCode}>{ecoCode}</a>{' '}
      <a href={lichessUrl} target="_blank" rel="noopener" class="eco-name-link" title={t('dashboard.opening.learn_link_tooltip')}>
        {nameJsx} <span class="eco-external-icon">↗</span>
      </a>
    </>
  );
}

const GAME_TYPE_LABELS_KEYS: Record<string, string> = {
  ultrabullet: 'dashboard.game_type.ultrabullet',
  bullet: 'dashboard.game_type.bullet',
  blitz: 'dashboard.game_type.blitz',
  rapid: 'dashboard.game_type.rapid',
  classical: 'dashboard.game_type.classical',
  correspondence: 'dashboard.game_type.correspondence',
  unknown: 'dashboard.game_type.unknown',
};

function gameTypeLabel(type: string): string {
  const key = GAME_TYPE_LABELS_KEYS[type];
  return key ? t(key) : type;
}

const PATTERN_LABEL_KEYS: Record<string, string> = {
  Fork: 'dashboard.tactical.fork', Pin: 'dashboard.tactical.pin',
  Skewer: 'dashboard.tactical.skewer', 'Discovered Attack': 'dashboard.tactical.discovery',
  'Discovered Check': 'dashboard.tactical.disc_check', 'Double Check': 'dashboard.tactical.double_check',
  'Hanging Piece': 'dashboard.tactical.hanging', 'Back Rank Threat': 'dashboard.tactical.back_rank',
  'Trapped Piece': 'dashboard.tactical.trapped', None: 'dashboard.tactical.other',
};

export function patternLabel(pattern: string): string {
  const key = PATTERN_LABEL_KEYS[pattern];
  return key ? t(key) : pattern;
}

function rateLabel(rate: number | null | undefined): string {
  return rate == null ? '—' : t('dashboard.chart.blunders_per_game', { rate: rate.toFixed(2) });
}

// A per-game rate from a handful of games is noise, so it never earns the highlight.
const MIN_RATE_GAMES = 10;

function blundersPerGamesDetail(blunders: number, games: number): string {
  return `${t('dashboard.coach.evidence.count', { count: blunders })} / ${t('dashboard.status.games', { count: games })}`;
}

function blunderDetail(count: number, avgCpLoss: number): string {
  return `${t('dashboard.coach.evidence.count', { count })} · ${t('dashboard.chart.avg_loss', { loss: (avgCpLoss / 100).toFixed(1) })}`;
}

export function PhaseBreakdown({ data }: { data: PhaseData }) {
  if (data.total_blunders <= 0 || data.by_phase.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_phase_data')}</div>;
  }

  return (
    <RankedBars
      rows={data.by_phase.map(p => ({
        key: p.phase,
        label: t(`chess.phase.${p.phase}`),
        value: p.count,
        display: `${String(p.percentage)}%`,
        detail: blunderDetail(p.count, p.avg_cp_loss),
      }))}
    />
  );
}

export function ColorBreakdown({ data }: { data: ColorData }) {
  if (data.by_color.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_color_data')}</div>;
  }

  return (
    <RankedBars
      rows={data.by_color.map(c => ({
        key: c.color,
        label: t('dashboard.chart.as_color', { color: t(`chess.color.${c.color}`) }),
        value: c.blunders_per_game ?? 0,
        display: rateLabel(c.blunders_per_game),
        detail: blundersPerGamesDetail(c.count, c.game_count),
        noLead: c.game_count < MIN_RATE_GAMES,
      }))}
    />
  );
}

export function GameTypeBreakdown({ data }: { data: GameTypeData }) {
  const played = data.by_game_type.filter(g => g.game_count > 0);
  if (played.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_game_type_data')}</div>;
  }

  return (
    <RankedBars
      rows={played.map(g => ({
        key: g.game_type,
        label: gameTypeLabel(g.game_type),
        value: g.blunders_per_game ?? 0,
        display: rateLabel(g.blunders_per_game),
        detail: blundersPerGamesDetail(g.count, g.game_count),
        noLead: g.game_count < MIN_RATE_GAMES,
      }))}
    />
  );
}

type EcoRow =
  | { kind: 'single'; id: string; item: OpeningItem }
  | { kind: 'child'; id: string; item: OpeningItem }
  | {
      kind: 'header';
      id: string;
      groupId: string;
      baseName: string;
      variationsLabel: string;
      totalCount: number;
      avgCpLoss: number;
      totalGames: number;
      blundersPerGame: number | null;
      isExpanded: boolean;
    };

export function EcoBreakdown({ data }: { data: EcoData }) {
  const [expandedGroups, setExpandedGroups] = useState(new Set<string>());

  if (data.total_blunders <= 0 || data.by_opening.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_opening_data')}</div>;
  }

  const grouped = groupOpeningsByBase(data.by_opening);

  const toggleGroup = (groupId: string) => {
    setExpandedGroups(prev => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const rows: EcoRow[] = [];
  for (const group of grouped) {
    if (group.variations.length === 1) {
      const item = group.variations[0];
      if (!item) continue;
      rows.push({ kind: 'single', id: item.eco_code, item });
      continue;
    }

    const groupId = `eco-group-${openingNameSlug(group.baseName)}`;
    const isExpanded = expandedGroups.has(groupId);
    rows.push({
      kind: 'header',
      id: groupId,
      groupId,
      baseName: group.baseName,
      variationsLabel: t('dashboard.opening.variations_count', { count: group.variations.length }),
      totalCount: group.totalCount,
      avgCpLoss: group.avgCpLoss,
      totalGames: group.totalGames,
      blundersPerGame: group.blundersPerGame,
      isExpanded,
    });
    if (isExpanded) {
      for (const item of group.variations) {
        rows.push({ kind: 'child', id: item.eco_code, item });
      }
    }
  }

  const columns: Column<EcoRow>[] = [
    {
      key: 'opening',
      header: t('dashboard.chart.eco_opening'),
      render: row => {
        if (row.kind === 'header') {
          return (
            <span
              class="eco-group-header"
              data-group={row.groupId}
              role="button"
              tabIndex={0}
              onClick={() => { toggleGroup(row.groupId); }}
              onKeyDown={(e: KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggleGroup(row.groupId);
                }
              }}
            >
              <span class="eco-group-toggle">{row.isExpanded ? '▼' : '▶'}</span>
              <span class="eco-name-base">{row.baseName}</span>
              <span class="eco-variations-badge">{row.variationsLabel}</span>
            </span>
          );
        }
        const name = renderOpeningName(row.item.eco_code, row.item.eco_name);
        return row.kind === 'child' ? <span class="eco-child-indent">{name}</span> : name;
      },
    },
    {
      key: 'rate',
      header: t('dashboard.chart.blunders_per_game_heading'),
      render: row => rateLabel(row.kind === 'header' ? row.blundersPerGame : row.item.blunders_per_game),
    },
    {
      key: 'blunders',
      header: t('dashboard.chart.eco_blunders'),
      render: row =>
        row.kind === 'header'
          ? String(row.totalCount)
          : <>{String(row.item.count)} <span class="eco-percent">({String(row.item.percentage)}%)</span></>,
    },
    {
      key: 'avg_loss',
      header: t('dashboard.chart.eco_avg_loss'),
      render: row =>
        `${(row.kind === 'header' ? row.avgCpLoss / 100 : row.item.avg_cp_loss / 100).toFixed(2)} pawns`,
    },
    {
      key: 'games',
      header: t('dashboard.chart.eco_games'),
      render: row => String(row.kind === 'header' ? row.totalGames : row.item.game_count),
    },
  ];

  return (
    <DataTable
      className="eco-table"
      columns={columns}
      rows={rows}
      rowKey={row => row.id}
    />
  );
}

export function TacticalBreakdown({ data }: { data: TacticalData }) {
  if (data.total_blunders <= 0 || data.by_pattern.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_tactical_data')}</div>;
  }

  const named = data.by_pattern.filter(p => p.count > 0 && !UNNAMED_PATTERNS.has(p.pattern)).sort((a, b) => b.count - a.count);
  const unnamed = data.by_pattern.filter(p => p.count > 0 && UNNAMED_PATTERNS.has(p.pattern));

  return (
    <RankedBars
      rows={[...named, ...unnamed].map(p => ({
        key: p.pattern,
        label: patternLabel(p.pattern),
        value: p.count,
        display: `${String(p.percentage)}%`,
        detail: blunderDetail(p.count, p.avg_cp_loss),
        muted: UNNAMED_PATTERNS.has(p.pattern),
      }))}
    />
  );
}

const DIFFICULTY_LABEL_KEYS: Record<string, string> = {
  easy: 'dashboard.difficulty.easy',
  medium: 'dashboard.difficulty.medium',
  hard: 'dashboard.difficulty.hard',
  unscored: 'dashboard.difficulty.unscored',
};

export function DifficultyBreakdown({ data }: { data: DifficultyData }) {
  if (data.total_blunders <= 0 || data.by_difficulty.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_difficulty_data')}</div>;
  }

  return (
    <RankedBars
      rows={data.by_difficulty.filter(d => d.count > 0).map(d => {
        const key = DIFFICULTY_LABEL_KEYS[d.difficulty];
        return {
          key: d.difficulty,
          label: key ? t(key) : d.difficulty,
          value: d.count,
          display: `${String(d.percentage)}%`,
          detail: blunderDetail(d.count, d.avg_cp_loss),
          muted: d.difficulty === 'unscored',
        };
      })}
    />
  );
}

const ZONES = [
  { range: '1–10', key: 'dashboard.collapse.zone_opening' },
  { range: '11–25', key: 'dashboard.collapse.zone_middle' },
  { range: '26+', key: 'dashboard.collapse.zone_late' },
];

export function CollapsePointBreakdown({ data }: { data: CollapsePointData }) {
  if (data.median_collapse_move === null || data.total_games_with_blunders <= 0) {
    return <div class="no-data-message">{t('dashboard.collapse.no_data')}</div>;
  }

  const totalGamesForClean = data.total_games_with_blunders + data.total_games_without_blunders;
  const cleanPercent = totalGamesForClean > 0
    ? Math.round(data.total_games_without_blunders / totalGamesForClean * 100)
    : 0;

  return (
    <>
      <div class="collapse-summary">
        <div class="collapse-big-number">{t('dashboard.collapse.median_move', { move: data.median_collapse_move })}</div>
        <div class="collapse-meta">
          <span>{t('dashboard.collapse.avg_move', { move: data.avg_collapse_move })}</span>
          <span class="collapse-separator">·</span>
          <span>{t('dashboard.collapse.games_with_blunders', { count: data.total_games_with_blunders })}</span>
        </div>
        <div class="collapse-clean">{t('dashboard.collapse.clean_games', { count: data.total_games_without_blunders, percentage: cleanPercent })}</div>
      </div>
      <div class="collapse-dist-title">{t('dashboard.collapse.distribution_title')}</div>
      <RankedBars
        rows={data.distribution.map(d => ({
          key: d.move_range,
          label: d.move_range,
          value: d.count,
          display: String(d.count),
        }))}
      />
      <p class="collapse-zone-key">
        {ZONES.map(zone => <span key={zone.key}><strong>{zone.range}</strong> {t(zone.key)}</span>)}
      </p>
    </>
  );
}

export function ConversionResilienceBreakdown({ data }: { data: ConversionResilienceData }) {
  if (data.games_with_advantage <= 0 && data.games_with_disadvantage <= 0) {
    return <div class="no-data-message">{t('dashboard.conversion.no_data')}</div>;
  }

  return (
    <RankedBars
      scale={100}
      highlight={false}
      rows={[
        {
          key: 'conversion',
          label: t('dashboard.conversion.title'),
          value: data.conversion_rate,
          display: `${String(data.conversion_rate)}%`,
          detail: t('dashboard.conversion.detail', { converted: data.games_converted, total: data.games_with_advantage }),
        },
        {
          key: 'resilience',
          label: t('dashboard.resilience.title'),
          value: data.resilience_rate,
          display: `${String(data.resilience_rate)}%`,
          detail: t('dashboard.resilience.detail', { saved: data.games_saved, total: data.games_with_disadvantage }),
        },
      ]}
    />
  );
}

export function TrapsSummary({ data }: { data: TrapStatsResponse }) {
  const { summary, stats } = data;

  if (summary.total_sprung <= 0 && summary.total_entered <= 0) {
    return (
      <div class="no-data-message">
        {t('traps.no_data')}<br />
        <a href="/traps">{t('traps.view_all')}</a>
      </div>
    );
  }

  const topItems = (summary.top_traps ?? []).slice(0, 3).map(tt => {
    const match = stats.find(s => s.trap_id === tt.trap_id);
    return (
      <span key={tt.trap_id} class="traps-tag">
        {match ? match.name : tt.trap_id} ({String(tt.count)})
      </span>
    );
  });

  return (
    <>
      <div class="traps-summary">
        <div><strong class="traps-summary-stat fell">{String(summary.total_sprung)}</strong> <span class="traps-summary-label">{t('traps.times_fell')}</span></div>
        <div><strong class="traps-summary-stat entered">{String(summary.total_entered)}</strong> <span class="traps-summary-label">{t('traps.times_entered')}</span></div>
      </div>
      {topItems.length > 0 && <div>{topItems}</div>}
      <a href="/traps" class="traps-view-all">{t('traps.view_all')} →</a>
    </>
  );
}
