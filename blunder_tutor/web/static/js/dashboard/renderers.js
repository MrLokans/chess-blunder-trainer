import { groupOpeningsByBase, openingNameSlug } from '../opening-group.js';

export function renderOpeningName(ecoCode, ecoName) {
  const colonIdx = ecoName.indexOf(': ');
  const lichessUrl = `https://lichess.org/opening/${openingNameSlug(ecoName)}`;
  const ecoUrl = `https://www.365chess.com/eco/${ecoCode}`;

  let nameHtml;
  if (colonIdx > -1) {
    const base = ecoName.substring(0, colonIdx);
    const variation = ecoName.substring(colonIdx + 2);
    const commaIdx = variation.indexOf(', ');
    if (commaIdx > -1) {
      nameHtml = `<span class="eco-name-base">${base}</span>: <span class="eco-name-variation">${variation.substring(0, commaIdx)}</span>, <span class="eco-name-subvariation">${variation.substring(commaIdx + 2)}</span>`;
    } else {
      nameHtml = `<span class="eco-name-base">${base}</span>: <span class="eco-name-variation">${variation}</span>`;
    }
  } else {
    nameHtml = `<span class="eco-name-base">${ecoName}</span>`;
  }

  return `<a href="${ecoUrl}" target="_blank" rel="noopener" class="eco-code" title="${ecoCode}">${ecoCode}</a> <a href="${lichessUrl}" target="_blank" rel="noopener" class="eco-name-link" title="${t('dashboard.opening.learn_link_tooltip')}">${nameHtml} <span class="eco-external-icon">↗</span></a>`;
}

function renderOpeningGroup(group) {
  if (group.variations.length === 1) {
    const item = group.variations[0];
    return `
      <tr>
        <td>${renderOpeningName(item.eco_code, item.eco_name)}</td>
        <td>${item.count} <span class="eco-percent">(${item.percentage}%)</span></td>
        <td>${(item.avg_cp_loss / 100).toFixed(2)} pawns</td>
        <td>${item.game_count}</td>
      </tr>`;
  }

  const groupId = `eco-group-${openingNameSlug(group.baseName)}`;
  const variationsLabel = t('dashboard.opening.variations_count', { count: group.variations.length });
  return `
    <tr class="eco-group-header" data-group="${groupId}">
      <td>
        <span class="eco-group-toggle">▶</span>
        <span class="eco-name-base">${group.baseName}</span>
        <span class="eco-variations-badge">${variationsLabel}</span>
      </td>
      <td>${group.totalCount}</td>
      <td>${(group.avgCpLoss / 100).toFixed(2)} pawns</td>
      <td>${group.totalGames}</td>
    </tr>
    ${group.variations.map(item => `
      <tr class="eco-group-child ${groupId}" style="display: none;">
        <td class="eco-child-indent">${renderOpeningName(item.eco_code, item.eco_name)}</td>
        <td>${item.count} <span class="eco-percent">(${item.percentage}%)</span></td>
        <td>${(item.avg_cp_loss / 100).toFixed(2)} pawns</td>
        <td>${item.game_count}</td>
      </tr>
    `).join('')}`;
}

export function initOpeningGroupToggles(container) {
  container.querySelectorAll('.eco-group-header').forEach(header => {
    header.style.cursor = 'pointer';
    header.addEventListener('click', () => {
      const groupId = header.dataset.group;
      const children = container.querySelectorAll(`.${groupId}`);
      const toggle = header.querySelector('.eco-group-toggle');
      const isExpanded = toggle.textContent === '▼';
      toggle.textContent = isExpanded ? '▶' : '▼';
      children.forEach(child => { child.style.display = isExpanded ? 'none' : ''; });
    });
  });
}

export function renderPhaseBreakdown(phaseData) {
  if (phaseData.total_blunders <= 0 || phaseData.by_phase.length === 0) {
    return { bar: '', cards: `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.chart.no_phase_data')}</div>`, showBar: false };
  }

  const bar = phaseData.by_phase
    .filter(p => p.percentage > 0)
    .map(p => `<div class="phase-bar-segment ${p.phase}" style="width: ${p.percentage}%">${p.percentage > 10 ? p.percentage + '%' : ''}</div>`)
    .join('');

  const cards = phaseData.by_phase.map(p => `
    <div class="phase-card ${p.phase}">
      <div class="phase-name">${t('chess.phase.' + p.phase)}</div>
      <div class="phase-count">${p.count}</div>
      <div class="phase-percent">${t('dashboard.chart.phase_percent', { percentage: p.percentage })}</div>
      <div class="phase-cpl">${t('dashboard.chart.avg_loss', { loss: (p.avg_cp_loss / 100).toFixed(1) })}</div>
    </div>
  `).join('');

  return { bar, cards, showBar: true };
}

export function renderColorBreakdown(colorData) {
  if (colorData.total_blunders <= 0 || colorData.by_color.length === 0) {
    return { bar: '', cards: `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.chart.no_color_data')}</div>`, showBar: false };
  }

  const bar = colorData.by_color
    .filter(c => c.percentage > 0)
    .map(c => `<div class="color-bar-segment ${c.color}" style="width: ${c.percentage}%">${c.percentage > 15 ? c.percentage + '%' : ''}</div>`)
    .join('');

  const cards = colorData.by_color.map(c => `
    <div class="color-card ${c.color}">
      <div class="color-name">${t('dashboard.chart.as_color', { color: t('chess.color.' + c.color) })}</div>
      <div class="color-count">${c.count}</div>
      <div class="color-percent">${t('dashboard.chart.phase_percent', { percentage: c.percentage })}</div>
      <div class="color-cpl">${t('dashboard.chart.avg_loss', { loss: (c.avg_cp_loss / 100).toFixed(1) })}</div>
    </div>
  `).join('');

  return { bar, cards, showBar: true };
}

const GAME_TYPE_LABELS_KEYS = {
  ultrabullet: 'dashboard.game_type.ultrabullet',
  bullet: 'dashboard.game_type.bullet',
  blitz: 'dashboard.game_type.blitz',
  rapid: 'dashboard.game_type.rapid',
  classical: 'dashboard.game_type.classical',
  correspondence: 'dashboard.game_type.correspondence',
  unknown: 'dashboard.game_type.unknown',
};

function gameTypeLabel(type) {
  const key = GAME_TYPE_LABELS_KEYS[type];
  return key ? t(key) : type;
}

export function renderGameTypeBreakdown(data) {
  if (data.total_blunders <= 0 || data.by_game_type.length === 0) {
    return { bar: '', legend: '', cards: `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.chart.no_game_type_data')}</div>`, showBar: false };
  }

  const bar = data.by_game_type
    .filter(g => g.percentage > 0)
    .map(g => `<div class="game-type-bar-segment ${g.game_type}" style="flex: ${g.percentage}">${g.percentage > 8 ? g.percentage + '%' : ''}</div>`)
    .join('');

  const usedTypes = data.by_game_type.filter(g => g.count > 0).map(g => g.game_type);
  const legend = usedTypes.map(type => `
    <div class="game-type-legend-item">
      <span class="game-type-legend-color ${type}"></span>
      <span>${gameTypeLabel(type)}</span>
    </div>
  `).join('');

  const cards = data.by_game_type
    .filter(g => g.count > 0)
    .map(g => `
      <div class="game-type-card ${g.game_type}">
        <div class="game-type-name">${gameTypeLabel(g.game_type)}</div>
        <div class="game-type-count">${g.count}</div>
        <div class="game-type-percent">${g.percentage}%</div>
      </div>
    `).join('');

  return { bar, legend, cards, showBar: true };
}

export function renderEcoBreakdown(ecoData) {
  if (ecoData.total_blunders <= 0 || ecoData.by_opening.length === 0) {
    return `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.chart.no_opening_data')}</div>`;
  }

  const grouped = groupOpeningsByBase(ecoData.by_opening);
  return `
    <table class="eco-table">
      <thead>
        <tr>
          <th>${t('dashboard.chart.eco_opening')}</th>
          <th>${t('dashboard.chart.eco_blunders')}</th>
          <th>${t('dashboard.chart.eco_avg_loss')}</th>
          <th>${t('dashboard.chart.eco_games')}</th>
        </tr>
      </thead>
      <tbody>
        ${grouped.map(group => renderOpeningGroup(group)).join('')}
      </tbody>
    </table>
  `;
}

const PATTERN_CLASSES = {
  Fork: 'fork', Pin: 'pin', Skewer: 'skewer',
  'Discovered Attack': 'discovered', 'Discovered Check': 'discovered', 'Double Check': 'discovered',
  'Hanging Piece': 'hanging', 'Back Rank Threat': 'back_rank',
  'Trapped Piece': 'other', None: 'other',
};

const PATTERN_LABEL_KEYS = {
  Fork: 'dashboard.tactical.fork', Pin: 'dashboard.tactical.pin',
  Skewer: 'dashboard.tactical.skewer', 'Discovered Attack': 'dashboard.tactical.discovery',
  'Discovered Check': 'dashboard.tactical.disc_check', 'Double Check': 'dashboard.tactical.double_check',
  'Hanging Piece': 'dashboard.tactical.hanging', 'Back Rank Threat': 'dashboard.tactical.back_rank',
  'Trapped Piece': 'dashboard.tactical.trapped', None: 'dashboard.tactical.other',
};

function patternLabel(pattern) {
  const key = PATTERN_LABEL_KEYS[pattern];
  return key ? t(key) : pattern;
}

export function renderTacticalBreakdown(data) {
  if (data.total_blunders <= 0 || data.by_pattern.length === 0) {
    return { bar: '', legend: '', cards: `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.chart.no_tactical_data')}</div>`, showBar: false };
  }

  const bar = data.by_pattern
    .filter(p => p.percentage > 0)
    .map(p => {
      const cls = PATTERN_CLASSES[p.pattern] || 'other';
      return `<div class="tactical-bar-segment ${cls}" style="flex: ${p.percentage}">${p.percentage > 8 ? p.percentage + '%' : ''}</div>`;
    })
    .join('');

  const uniqueClasses = [...new Set(data.by_pattern.map(p => PATTERN_CLASSES[p.pattern] || 'other'))];
  const legend = uniqueClasses.map(cls => {
    const label = Object.entries(PATTERN_CLASSES).find(([_k, v]) => v === cls)?.[0] || cls;
    return `
      <div class="tactical-legend-item">
        <span class="tactical-legend-color ${cls}"></span>
        <span>${patternLabel(label)}</span>
      </div>
    `;
  }).join('');

  const cards = data.by_pattern
    .filter(p => p.count > 0)
    .map(p => {
      const cls = PATTERN_CLASSES[p.pattern] || 'other';
      return `
        <div class="tactical-card ${cls}">
          <div class="tactical-name">${patternLabel(p.pattern)}</div>
          <div class="tactical-count">${p.count}</div>
          <div class="tactical-percent">${p.percentage}%</div>
        </div>
      `;
    }).join('');

  return { bar, legend, cards, showBar: true };
}

export function renderDifficultyBreakdown(data) {
  const diffToClass = { easy: 'diff-easy', medium: 'diff-medium', hard: 'diff-hard', unscored: 'diff-unscored' };
  const diffLabels = {
    easy: t('dashboard.difficulty.easy'), medium: t('dashboard.difficulty.medium'),
    hard: t('dashboard.difficulty.hard'), unscored: t('dashboard.difficulty.unscored'),
  };

  if (data.total_blunders <= 0 || data.by_difficulty.length === 0) {
    return { bar: '', legend: '', cards: `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.chart.no_difficulty_data')}</div>`, showBar: false };
  }

  const bar = data.by_difficulty
    .filter(d => d.percentage > 0)
    .map(d => {
      const cls = diffToClass[d.difficulty] || 'diff-unscored';
      return `<div class="difficulty-bar-segment ${cls}" style="flex: ${d.percentage}">${d.percentage > 8 ? d.percentage + '%' : ''}</div>`;
    })
    .join('');

  const legend = data.by_difficulty
    .filter(d => d.count > 0)
    .map(d => {
      const cls = diffToClass[d.difficulty] || 'diff-unscored';
      return `
        <div class="difficulty-legend-item">
          <span class="difficulty-legend-color ${cls}"></span>
          <span>${diffLabels[d.difficulty] || d.difficulty}</span>
        </div>
      `;
    })
    .join('');

  const cards = data.by_difficulty
    .filter(d => d.count > 0)
    .map(d => {
      const cls = diffToClass[d.difficulty] || 'diff-unscored';
      const label = diffLabels[d.difficulty] || d.difficulty;
      return `
        <div class="difficulty-card ${cls}">
          <div class="difficulty-name">${label}</div>
          <div class="difficulty-count">${d.count}</div>
          <div class="difficulty-percent">${d.percentage}%</div>
          <div class="difficulty-avg-loss">${t('dashboard.chart.avg_loss', { loss: (d.avg_cp_loss / 100).toFixed(1) })}</div>
        </div>
      `;
    })
    .join('');

  return { bar, legend, cards, showBar: true };
}

export function renderCollapsePoint(cpData) {
  if (cpData.avg_collapse_move === null || cpData.total_games_with_blunders <= 0) {
    return `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.collapse.no_data')}</div>`;
  }

  const totalGamesForClean = cpData.total_games_with_blunders + cpData.total_games_without_blunders;
  const cleanPercent = totalGamesForClean > 0
    ? Math.round(cpData.total_games_without_blunders / totalGamesForClean * 100) : 0;
  const maxCount = Math.max(...cpData.distribution.map(d => d.count), 1);

  const zoneColor = (label) => {
    const start = parseInt(label.split('-')[0]);
    if (start <= 10) return 'var(--success, #2D8F3E)';
    if (start <= 25) return 'var(--warning, #F2C12E)';
    return 'var(--error, #D42828)';
  };

  const zoneLabel = (label) => {
    const start = parseInt(label.split('-')[0]);
    if (start <= 10) return t('dashboard.collapse.zone_opening');
    if (start <= 25) return t('dashboard.collapse.zone_middle');
    return t('dashboard.collapse.zone_late');
  };

  const barsHtml = cpData.distribution.map(d => {
    const pct = Math.round(d.count / maxCount * 100);
    const color = zoneColor(d.move_range);
    return `
      <div class="collapse-bar-row">
        <span class="collapse-bar-label">${d.move_range}</span>
        <div class="collapse-bar-track">
          <div class="collapse-bar-fill" style="width: ${pct}%; background: ${color};" title="${zoneLabel(d.move_range)}"></div>
        </div>
        <span class="collapse-bar-count">${d.count}</span>
      </div>
    `;
  }).join('');

  return `
    <div class="collapse-summary">
      <div class="collapse-big-number">${t('dashboard.collapse.avg_move', { move: cpData.avg_collapse_move })}</div>
      <div class="collapse-meta">
        <span>${t('dashboard.collapse.median_move', { move: cpData.median_collapse_move })}</span>
        <span class="collapse-separator">·</span>
        <span>${t('dashboard.collapse.games_with_blunders', { count: cpData.total_games_with_blunders })}</span>
      </div>
      <div class="collapse-clean">${t('dashboard.collapse.clean_games', { count: cpData.total_games_without_blunders, percentage: cleanPercent })}</div>
    </div>
    <div class="collapse-distribution">
      <div class="collapse-dist-title">${t('dashboard.collapse.distribution_title')}</div>
      ${barsHtml}
    </div>
    <div class="collapse-zone-legend">
      <span class="collapse-zone-item"><span class="collapse-zone-dot" style="background: var(--success, #2D8F3E);"></span>${t('dashboard.collapse.zone_opening')}</span>
      <span class="collapse-zone-item"><span class="collapse-zone-dot" style="background: var(--warning, #F2C12E);"></span>${t('dashboard.collapse.zone_middle')}</span>
      <span class="collapse-zone-item"><span class="collapse-zone-dot" style="background: var(--error, #D42828);"></span>${t('dashboard.collapse.zone_late')}</span>
    </div>
  `;
}

export function renderConversionResilience(crData) {
  if (crData.games_with_advantage <= 0 && crData.games_with_disadvantage <= 0) {
    return `<div style="text-align: center; padding: 20px; color: var(--text-muted);">${t('dashboard.conversion.no_data')}</div>`;
  }

  const conversionColor = crData.conversion_rate >= 70 ? 'var(--success, #2D8F3E)' : crData.conversion_rate >= 50 ? 'var(--warning, #F2C12E)' : 'var(--error, #D42828)';
  const resilienceColor = crData.resilience_rate >= 20 ? 'var(--success, #2D8F3E)' : crData.resilience_rate >= 10 ? 'var(--warning, #F2C12E)' : 'var(--error, #D42828)';

  return `
    <div class="cr-metrics">
      <div class="cr-metric-card">
        <div class="cr-metric-label">${t('dashboard.conversion.title')}</div>
        <div class="cr-metric-value" style="color: ${conversionColor}">${crData.conversion_rate}%</div>
        <div class="cr-metric-detail">${t('dashboard.conversion.detail', { converted: crData.games_converted, total: crData.games_with_advantage })}</div>
      </div>
      <div class="cr-metric-card">
        <div class="cr-metric-label">${t('dashboard.resilience.title')}</div>
        <div class="cr-metric-value" style="color: ${resilienceColor}">${crData.resilience_rate}%</div>
        <div class="cr-metric-detail">${t('dashboard.resilience.detail', { saved: crData.games_saved, total: crData.games_with_disadvantage })}</div>
      </div>
    </div>
  `;
}

export function renderTrapsSummary(trapsData) {
  const summary = trapsData.summary || {};
  const stats = trapsData.stats || [];

  if (summary.total_sprung <= 0 && summary.total_entered <= 0) {
    return `<div style="text-align:center;padding:20px;color:var(--text-muted);">${t('traps.no_data')}<br><a href="/traps">${t('traps.view_all')}</a></div>`;
  }

  const topItems = (summary.top_traps || []).slice(0, 3).map(tt => {
    const match = stats.find(s => s.trap_id === tt.trap_id);
    return `<span style="display:inline-block;background:var(--primary);color:var(--bg);padding:2px 8px;border-radius:var(--radius);font-size:0.8rem;margin-right:4px;">${match ? match.name : tt.trap_id} (${tt.count})</span>`;
  }).join('');

  return `
    <div style="display:flex;gap:var(--space-4);flex-wrap:wrap;margin-bottom:var(--space-2);">
      <div><strong style="font-size:1.5rem;color:var(--error);">${summary.total_sprung}</strong> <span style="color:var(--text-muted);font-size:0.85rem;">${t('traps.times_fell')}</span></div>
      <div><strong style="font-size:1.5rem;color:var(--warning);">${summary.total_entered}</strong> <span style="color:var(--text-muted);font-size:0.85rem;">${t('traps.times_entered')}</span></div>
    </div>
    ${topItems ? `<div>${topItems}</div>` : ''}
    <a href="/traps" style="display:inline-block;margin-top:var(--space-2);color:var(--primary);">${t('traps.view_all')} →</a>
  `;
}

export function renderGameBreakdown(items) {
  return items.map(row => `
    <tr>
      <td>${row.source}</td>
      <td>${row.username}</td>
      <td>${row.total_games}</td>
      <td>${row.analyzed_games}</td>
      <td>${row.pending_games}</td>
    </tr>
  `).join('');
}
