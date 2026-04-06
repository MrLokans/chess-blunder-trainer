import { useState } from 'preact/hooks';
import { groupOpeningsByBase, openingNameSlug } from '../shared/opening-group';
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
  TrapsData,
  GameBreakdownItem,
} from './types';

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

const PATTERN_CLASSES: Record<string, string> = {
  Fork: 'fork', Pin: 'pin', Skewer: 'skewer',
  'Discovered Attack': 'discovered', 'Discovered Check': 'discovered', 'Double Check': 'discovered',
  'Hanging Piece': 'hanging', 'Back Rank Threat': 'back_rank',
  'Trapped Piece': 'other', None: 'other',
};

const PATTERN_LABEL_KEYS: Record<string, string> = {
  Fork: 'dashboard.tactical.fork', Pin: 'dashboard.tactical.pin',
  Skewer: 'dashboard.tactical.skewer', 'Discovered Attack': 'dashboard.tactical.discovery',
  'Discovered Check': 'dashboard.tactical.disc_check', 'Double Check': 'dashboard.tactical.double_check',
  'Hanging Piece': 'dashboard.tactical.hanging', 'Back Rank Threat': 'dashboard.tactical.back_rank',
  'Trapped Piece': 'dashboard.tactical.trapped', None: 'dashboard.tactical.other',
};

function patternLabel(pattern: string): string {
  const key = PATTERN_LABEL_KEYS[pattern];
  return key ? t(key) : pattern;
}

export function PhaseBreakdown({ data }: { data: PhaseData }) {
  if (data.total_blunders <= 0 || data.by_phase.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_phase_data')}</div>;
  }

  return (
    <>
      <div class="phase-bar">
        {data.by_phase
          .filter(p => p.percentage > 0)
          .map(p => (
            <div key={p.phase} class={`phase-bar-segment ${p.phase}`} style={{ width: `${String(p.percentage)}%` }}>
              {p.percentage > 10 ? `${String(p.percentage)}%` : ''}
            </div>
          ))}
      </div>
      <div class="phase-breakdown">
        {data.by_phase.map(p => (
          <div key={p.phase} class={`phase-card ${p.phase}`}>
            <div class="phase-name">{t(`chess.phase.${p.phase}`)}</div>
            <div class="phase-count">{String(p.count)}</div>
            <div class="phase-percent">{t('dashboard.chart.phase_percent', { percentage: p.percentage })}</div>
            <div class="phase-cpl">{t('dashboard.chart.avg_loss', { loss: (p.avg_cp_loss / 100).toFixed(1) })}</div>
          </div>
        ))}
      </div>
    </>
  );
}

export function ColorBreakdown({ data }: { data: ColorData }) {
  if (data.total_blunders <= 0 || data.by_color.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_color_data')}</div>;
  }

  return (
    <>
      <div class="color-bar">
        {data.by_color
          .filter(c => c.percentage > 0)
          .map(c => (
            <div key={c.color} class={`color-bar-segment ${c.color}`} style={{ width: `${String(c.percentage)}%` }}>
              {c.percentage > 15 ? `${String(c.percentage)}%` : ''}
            </div>
          ))}
      </div>
      <div class="color-breakdown">
        {data.by_color.map(c => (
          <div key={c.color} class={`color-card ${c.color}`}>
            <div class="color-name">{t('dashboard.chart.as_color', { color: t(`chess.color.${c.color}`) })}</div>
            <div class="color-count">{String(c.count)}</div>
            <div class="color-percent">{t('dashboard.chart.phase_percent', { percentage: c.percentage })}</div>
            <div class="color-cpl">{t('dashboard.chart.avg_loss', { loss: (c.avg_cp_loss / 100).toFixed(1) })}</div>
          </div>
        ))}
      </div>
    </>
  );
}

export function GameTypeBreakdown({ data }: { data: GameTypeData }) {
  if (data.total_blunders <= 0 || data.by_game_type.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_game_type_data')}</div>;
  }

  const usedTypes = data.by_game_type.filter(g => g.count > 0).map(g => g.game_type);

  return (
    <>
      <div class="game-type-bar">
        {data.by_game_type
          .filter(g => g.percentage > 0)
          .map(g => (
            <div key={g.game_type} class={`game-type-bar-segment ${g.game_type}`} style={{ flex: String(g.percentage) }}>
              {g.percentage > 8 ? `${String(g.percentage)}%` : ''}
            </div>
          ))}
      </div>
      <div class="game-type-legend">
        {usedTypes.map(type => (
          <div key={type} class="game-type-legend-item">
            <span class={`game-type-legend-color ${type}`}></span>
            <span>{gameTypeLabel(type)}</span>
          </div>
        ))}
      </div>
      <div class="game-type-breakdown">
        {data.by_game_type
          .filter(g => g.count > 0)
          .map(g => (
            <div key={g.game_type} class={`game-type-card ${g.game_type}`}>
              <div class="game-type-name">{gameTypeLabel(g.game_type)}</div>
              <div class="game-type-count">{String(g.count)}</div>
              <div class="game-type-percent">{`${String(g.percentage)}%`}</div>
            </div>
          ))}
      </div>
    </>
  );
}

interface OpeningRowProps {
  item: OpeningItem;
  isChild?: boolean;
  hidden?: boolean;
}

function OpeningRow({ item, isChild, hidden }: OpeningRowProps) {
  return (
    <tr class={isChild ? 'eco-group-child' : ''} style={hidden ? { display: 'none' } : undefined}>
      <td class={isChild ? 'eco-child-indent' : ''}>{renderOpeningName(item.eco_code, item.eco_name)}</td>
      <td>{String(item.count)} <span class="eco-percent">({String(item.percentage)}%)</span></td>
      <td>{(item.avg_cp_loss / 100).toFixed(2)} pawns</td>
      <td>{String(item.game_count)}</td>
    </tr>
  );
}

export function EcoBreakdown({ data }: { data: EcoData }) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());

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

  return (
    <table class="eco-table">
      <thead>
        <tr>
          <th>{t('dashboard.chart.eco_opening')}</th>
          <th>{t('dashboard.chart.eco_blunders')}</th>
          <th>{t('dashboard.chart.eco_avg_loss')}</th>
          <th>{t('dashboard.chart.eco_games')}</th>
        </tr>
      </thead>
      <tbody>
        {grouped.map(group => {
          if (group.variations.length === 1) {
            const item = group.variations[0]!;
            return <OpeningRow key={item.eco_code} item={item} />;
          }

          const groupId = `eco-group-${openingNameSlug(group.baseName)}`;
          const isExpanded = expandedGroups.has(groupId);
          const variationsLabel = t('dashboard.opening.variations_count', { count: group.variations.length });

          return (
            <>
              <tr
                key={groupId}
                class="eco-group-header"
                data-group={groupId}
                onClick={() => { toggleGroup(groupId); }}
              >
                <td>
                  <span class="eco-group-toggle">{isExpanded ? '▼' : '▶'}</span>
                  <span class="eco-name-base">{group.baseName}</span>
                  <span class="eco-variations-badge">{variationsLabel}</span>
                </td>
                <td>{String(group.totalCount)}</td>
                <td>{(group.avgCpLoss / 100).toFixed(2)} pawns</td>
                <td>{String(group.totalGames)}</td>
              </tr>
              {group.variations.map(item => (
                <OpeningRow
                  key={item.eco_code}
                  item={item}
                  isChild
                  hidden={!isExpanded}
                />
              ))}
            </>
          );
        })}
      </tbody>
    </table>
  );
}

export function TacticalBreakdown({ data }: { data: TacticalData }) {
  if (data.total_blunders <= 0 || data.by_pattern.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_tactical_data')}</div>;
  }

  const uniqueClasses = [...new Set(data.by_pattern.map(p => PATTERN_CLASSES[p.pattern] ?? 'other'))];

  return (
    <>
      <div class="tactical-bar">
        {data.by_pattern
          .filter(p => p.percentage > 0)
          .map(p => {
            const cls = PATTERN_CLASSES[p.pattern] ?? 'other';
            return (
              <div key={p.pattern} class={`tactical-bar-segment ${cls}`} style={{ flex: String(p.percentage) }}>
                {p.percentage > 8 ? `${String(p.percentage)}%` : ''}
              </div>
            );
          })}
      </div>
      <div class="tactical-legend">
        {uniqueClasses.map(cls => {
          const label = Object.entries(PATTERN_CLASSES).find(([_k, v]) => v === cls)?.[0] ?? cls;
          return (
            <div key={cls} class="tactical-legend-item">
              <span class={`tactical-legend-color ${cls}`}></span>
              <span>{patternLabel(label)}</span>
            </div>
          );
        })}
      </div>
      <div class="tactical-breakdown">
        {data.by_pattern
          .filter(p => p.count > 0)
          .map(p => {
            const cls = PATTERN_CLASSES[p.pattern] ?? 'other';
            return (
              <div key={p.pattern} class={`tactical-card ${cls}`}>
                <div class="tactical-name">{patternLabel(p.pattern)}</div>
                <div class="tactical-count">{String(p.count)}</div>
                <div class="tactical-percent">{`${String(p.percentage)}%`}</div>
              </div>
            );
          })}
      </div>
    </>
  );
}

export function DifficultyBreakdown({ data }: { data: DifficultyData }) {
  const diffToClass: Record<string, string> = {
    easy: 'diff-easy', medium: 'diff-medium', hard: 'diff-hard', unscored: 'diff-unscored',
  };
  const diffLabels: Record<string, string> = {
    easy: t('dashboard.difficulty.easy'),
    medium: t('dashboard.difficulty.medium'),
    hard: t('dashboard.difficulty.hard'),
    unscored: t('dashboard.difficulty.unscored'),
  };

  if (data.total_blunders <= 0 || data.by_difficulty.length === 0) {
    return <div class="no-data-message">{t('dashboard.chart.no_difficulty_data')}</div>;
  }

  return (
    <>
      <div class="difficulty-bar">
        {data.by_difficulty
          .filter(d => d.percentage > 0)
          .map(d => {
            const cls = diffToClass[d.difficulty] ?? 'diff-unscored';
            return (
              <div key={d.difficulty} class={`difficulty-bar-segment ${cls}`} style={{ flex: String(d.percentage) }}>
                {d.percentage > 8 ? `${String(d.percentage)}%` : ''}
              </div>
            );
          })}
      </div>
      <div class="difficulty-legend">
        {data.by_difficulty
          .filter(d => d.count > 0)
          .map(d => {
            const cls = diffToClass[d.difficulty] ?? 'diff-unscored';
            return (
              <div key={d.difficulty} class="difficulty-legend-item">
                <span class={`difficulty-legend-color ${cls}`}></span>
                <span>{diffLabels[d.difficulty] ?? d.difficulty}</span>
              </div>
            );
          })}
      </div>
      <div class="difficulty-breakdown">
        {data.by_difficulty
          .filter(d => d.count > 0)
          .map(d => {
            const cls = diffToClass[d.difficulty] ?? 'diff-unscored';
            const label = diffLabels[d.difficulty] ?? d.difficulty;
            return (
              <div key={d.difficulty} class={`difficulty-card ${cls}`}>
                <div class="difficulty-name">{label}</div>
                <div class="difficulty-count">{String(d.count)}</div>
                <div class="difficulty-percent">{`${String(d.percentage)}%`}</div>
                <div class="difficulty-avg-loss">{t('dashboard.chart.avg_loss', { loss: (d.avg_cp_loss / 100).toFixed(1) })}</div>
              </div>
            );
          })}
      </div>
    </>
  );
}

function zoneColor(label: string): string {
  const start = parseInt(label.split('-')[0]!);
  if (start <= 10) return 'var(--success, #2D8F3E)';
  if (start <= 25) return 'var(--warning, #F2C12E)';
  return 'var(--error, #D42828)';
}

function zoneLabel(label: string): string {
  const start = parseInt(label.split('-')[0]!);
  if (start <= 10) return t('dashboard.collapse.zone_opening');
  if (start <= 25) return t('dashboard.collapse.zone_middle');
  return t('dashboard.collapse.zone_late');
}

export function CollapsePointBreakdown({ data }: { data: CollapsePointData }) {
  if (data.avg_collapse_move === null || data.total_games_with_blunders <= 0) {
    return <div class="no-data-message">{t('dashboard.collapse.no_data')}</div>;
  }

  const totalGamesForClean = data.total_games_with_blunders + data.total_games_without_blunders;
  const cleanPercent = totalGamesForClean > 0
    ? Math.round(data.total_games_without_blunders / totalGamesForClean * 100)
    : 0;
  const maxCount = Math.max(...data.distribution.map(d => d.count), 1);

  return (
    <>
      <div class="collapse-summary">
        <div class="collapse-big-number">{t('dashboard.collapse.avg_move', { move: data.avg_collapse_move })}</div>
        <div class="collapse-meta">
          <span>{t('dashboard.collapse.median_move', { move: data.median_collapse_move })}</span>
          <span class="collapse-separator">·</span>
          <span>{t('dashboard.collapse.games_with_blunders', { count: data.total_games_with_blunders })}</span>
        </div>
        <div class="collapse-clean">{t('dashboard.collapse.clean_games', { count: data.total_games_without_blunders, percentage: cleanPercent })}</div>
      </div>
      <div class="collapse-distribution">
        <div class="collapse-dist-title">{t('dashboard.collapse.distribution_title')}</div>
        {data.distribution.map(d => {
          const pct = Math.round(d.count / maxCount * 100);
          const color = zoneColor(d.move_range);
          return (
            <div key={d.move_range} class="collapse-bar-row">
              <span class="collapse-bar-label">{d.move_range}</span>
              <div class="collapse-bar-track">
                <div class="collapse-bar-fill" style={{ width: `${String(pct)}%`, background: color }} title={zoneLabel(d.move_range)}></div>
              </div>
              <span class="collapse-bar-count">{String(d.count)}</span>
            </div>
          );
        })}
      </div>
      <div class="collapse-zone-legend">
        <span class="collapse-zone-item">
          <span class="collapse-zone-dot" style={{ background: 'var(--success, #2D8F3E)' }}></span>
          {t('dashboard.collapse.zone_opening')}
        </span>
        <span class="collapse-zone-item">
          <span class="collapse-zone-dot" style={{ background: 'var(--warning, #F2C12E)' }}></span>
          {t('dashboard.collapse.zone_middle')}
        </span>
        <span class="collapse-zone-item">
          <span class="collapse-zone-dot" style={{ background: 'var(--error, #D42828)' }}></span>
          {t('dashboard.collapse.zone_late')}
        </span>
      </div>
    </>
  );
}

export function ConversionResilienceBreakdown({ data }: { data: ConversionResilienceData }) {
  if (data.games_with_advantage <= 0 && data.games_with_disadvantage <= 0) {
    return <div class="no-data-message">{t('dashboard.conversion.no_data')}</div>;
  }

  const conversionColor = data.conversion_rate >= 70
    ? 'var(--success, #2D8F3E)'
    : data.conversion_rate >= 50
      ? 'var(--warning, #F2C12E)'
      : 'var(--error, #D42828)';

  const resilienceColor = data.resilience_rate >= 20
    ? 'var(--success, #2D8F3E)'
    : data.resilience_rate >= 10
      ? 'var(--warning, #F2C12E)'
      : 'var(--error, #D42828)';

  return (
    <div class="cr-metrics">
      <div class="cr-metric-card">
        <div class="cr-metric-label">{t('dashboard.conversion.title')}</div>
        <div class="cr-metric-value" style={{ color: conversionColor }}>{`${String(data.conversion_rate)}%`}</div>
        <div class="cr-metric-detail">{t('dashboard.conversion.detail', { converted: data.games_converted, total: data.games_with_advantage })}</div>
      </div>
      <div class="cr-metric-card">
        <div class="cr-metric-label">{t('dashboard.resilience.title')}</div>
        <div class="cr-metric-value" style={{ color: resilienceColor }}>{`${String(data.resilience_rate)}%`}</div>
        <div class="cr-metric-detail">{t('dashboard.resilience.detail', { saved: data.games_saved, total: data.games_with_disadvantage })}</div>
      </div>
    </div>
  );
}

export function TrapsSummary({ data }: { data: TrapsData }) {
  const summary = data.summary ?? { total_sprung: 0, total_entered: 0 };
  const stats = data.stats ?? [];

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

export function GameBreakdownTable({ items }: { items: GameBreakdownItem[] }) {
  if (items.length === 0) {
    return <>{t('dashboard.no_data')}</>;
  }

  return (
    <>
      {items.map((row, i) => (
        <tr key={i}>
          <td>{row.source}</td>
          <td>{row.username}</td>
          <td>{String(row.total_games)}</td>
          <td>{String(row.analyzed_games)}</td>
          <td>{String(row.pending_games)}</td>
        </tr>
      ))}
    </>
  );
}
