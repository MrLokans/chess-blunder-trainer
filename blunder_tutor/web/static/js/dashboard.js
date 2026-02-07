import { WebSocketClient } from './websocket-client.js';
import { FilterPersistence } from './filter-persistence.js';
import { loadConfiguredUsernames } from './usernames.js';
import { loadHeatmap } from './heatmap.js';
import { client } from './api.js';
import { groupOpeningsByBase, openingNameSlug } from './opening-group.js';
import { hasFeature } from './features.js';

const wsClient = new WebSocketClient();

let currentDateFrom = null;
let currentDateTo = null;
let configuredUsernames = {};
let dateChart = null;
let hourChart = null;
let currentGameTypeFilters = ['bullet', 'blitz', 'rapid', 'classical'];

const gameTypeFilter = new FilterPersistence({
  storageKey: 'dashboard-game-type-filters',
  checkboxSelector: '.game-type-filter',
  defaultValues: ['bullet', 'blitz', 'rapid', 'classical']
});

function getFirstUsername() {
  return configuredUsernames.lichess_username || configuredUsernames.chesscom_username || null;
}

function getPresetDates(preset) {
  const now = new Date();
  const to = now.toISOString().split('T')[0];
  let from = null;

  switch (preset) {
    case '7d':
      from = new Date(now - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case '30d':
      from = new Date(now - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case '90d':
      from = new Date(now - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case '1y':
      from = new Date(now - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      break;
    case 'all':
      return { from: null, to: null };
  }
  return { from, to };
}

function setPreset(preset) {
  const dates = getPresetDates(preset);
  document.getElementById('dateFrom').value = dates.from || '';
  document.getElementById('dateTo').value = dates.to || '';
  currentDateFrom = dates.from;
  currentDateTo = dates.to;

  document.querySelectorAll('.filter-presets button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === preset);
  });

  loadStats();
}

function applyDateFilter() {
  currentDateFrom = document.getElementById('dateFrom').value || null;
  currentDateTo = document.getElementById('dateTo').value || null;

  document.querySelectorAll('.filter-presets button').forEach(btn => btn.classList.remove('active'));

  loadStats();
}

function clearDateFilter() {
  document.getElementById('dateFrom').value = '';
  document.getElementById('dateTo').value = '';
  currentDateFrom = null;
  currentDateTo = null;

  document.querySelectorAll('.filter-presets button').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.preset === 'all');
  });

  loadStats();
}

function dateParams() {
  const params = {};
  if (currentDateFrom) params.start_date = currentDateFrom;
  if (currentDateTo) params.end_date = currentDateTo;
  return params;
}

function dateAndGameTypeParams() {
  const params = dateParams();
  if (currentGameTypeFilters.length > 0 && currentGameTypeFilters.length < 4) {
    params.game_types = currentGameTypeFilters;
  }
  return params;
}

function renderOpeningName(ecoCode, ecoName) {
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

function initOpeningGroupToggles(container) {
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

async function loadStats() {
  try {
    const overview = await client.stats.overview();

    document.getElementById('totalGames').textContent = overview.total_games || 0;
    document.getElementById('analyzedGames').textContent = overview.analyzed_games || 0;
    document.getElementById('totalBlunders').textContent = overview.total_blunders || 0;

    const totalGames = overview.total_games || 0;
    const analyzedGames = overview.analyzed_games || 0;
    const progressPercent = totalGames > 0 ? Math.round((analyzedGames / totalGames) * 100) : 0;

    document.getElementById('progressPercent').textContent = progressPercent + '%';
    document.getElementById('progressFill').style.width = progressPercent + '%';

    const analysisStatus = await client.analysis.status();

    const statusEl = document.getElementById('analysisJobStatus');
    if (analysisStatus.status === 'running') {
      const percent = analysisStatus.progress_total > 0
        ? Math.round((analysisStatus.progress_current / analysisStatus.progress_total) * 100)
        : 0;
      statusEl.textContent = t('dashboard.analysis.running', { current: analysisStatus.progress_current || 0, total: analysisStatus.progress_total || 0, percent });
      statusEl.style.color = 'var(--primary)';
    } else if (analysisStatus.status === 'completed') {
      statusEl.textContent = t('dashboard.analysis.completed');
      statusEl.style.color = 'var(--success)';
    } else if (analysisStatus.status === 'failed') {
      statusEl.innerHTML = t('dashboard.analysis.failed') + ' <button class="btn btn-sm" id="retryAnalysisBtn" style="margin-left: 8px; padding: 4px 10px; font-size: 0.75rem;">' + t('dashboard.analysis.retry') + '</button>';
      statusEl.style.color = 'var(--error)';
      document.getElementById('retryAnalysisBtn').addEventListener('click', retryAnalysis);
    } else {
      statusEl.textContent = '';
    }

    if (hasFeature('dashboard.accuracy')) {
      await loadDateChart();
      await loadHourChart();
    }

    // Blunders by phase
    if (hasFeature('dashboard.phase_breakdown') && document.getElementById('phaseBreakdown')) {
    const phaseData = await client.stats.blundersByPhase(dateAndGameTypeParams());

    const phaseBreakdown = document.getElementById('phaseBreakdown');
    const phaseBarContainer = document.getElementById('phaseBarContainer');
    const phaseBar = document.getElementById('phaseBar');

    if (phaseData.total_blunders > 0 && phaseData.by_phase.length > 0) {
      phaseBarContainer.style.display = 'block';

      phaseBar.innerHTML = phaseData.by_phase
        .filter(p => p.percentage > 0)
        .map(p => `<div class="phase-bar-segment ${p.phase}" style="width: ${p.percentage}%">${p.percentage > 10 ? p.percentage + '%' : ''}</div>`)
        .join('');

      phaseBreakdown.innerHTML = phaseData.by_phase.map(p => `
        <div class="phase-card ${p.phase}">
          <div class="phase-name">${t('chess.phase.' + p.phase)}</div>
          <div class="phase-count">${p.count}</div>
          <div class="phase-percent">${t('dashboard.chart.phase_percent', { percentage: p.percentage })}</div>
          <div class="phase-cpl">${t('dashboard.chart.avg_loss', { loss: (p.avg_cp_loss / 100).toFixed(1) })}</div>
        </div>
      `).join('');
    } else {
      phaseBarContainer.style.display = 'none';
      phaseBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">' + t('dashboard.chart.no_phase_data') + '</div>';
    }
    }

    // Blunders by color
    const username = getFirstUsername();
    const colorParams = { ...dateParams() };
    if (username) colorParams.username = username;
    const colorData = await client.stats.blundersByColor(colorParams);

    const colorBreakdown = document.getElementById('colorBreakdown');
    const colorBarContainer = document.getElementById('colorBarContainer');
    const colorBar = document.getElementById('colorBar');

    if (colorData.total_blunders > 0 && colorData.by_color.length > 0) {
      colorBarContainer.style.display = 'block';

      colorBar.innerHTML = colorData.by_color
        .filter(c => c.percentage > 0)
        .map(c => `<div class="color-bar-segment ${c.color}" style="width: ${c.percentage}%">${c.percentage > 15 ? c.percentage + '%' : ''}</div>`)
        .join('');

      colorBreakdown.innerHTML = colorData.by_color.map(c => `
        <div class="color-card ${c.color}">
          <div class="color-name">${t('dashboard.chart.as_color', { color: t('chess.color.' + c.color) })}</div>
          <div class="color-count">${c.count}</div>
          <div class="color-percent">${t('dashboard.chart.phase_percent', { percentage: c.percentage })}</div>
          <div class="color-cpl">${t('dashboard.chart.avg_loss', { loss: (c.avg_cp_loss / 100).toFixed(1) })}</div>
        </div>
      `).join('');
    } else {
      colorBarContainer.style.display = 'none';
      colorBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">' + t('dashboard.chart.no_color_data') + '</div>';
    }

    // Blunders by game type
    const gameTypeData = await client.stats.blundersByGameType(dateParams());

    const gameTypeBreakdown = document.getElementById('gameTypeBreakdown');
    const gameTypeBarContainer = document.getElementById('gameTypeBarContainer');
    const gameTypeBar = document.getElementById('gameTypeBar');
    const gameTypeLegend = document.getElementById('gameTypeLegend');

    const gameTypeLabels = {
      'ultrabullet': t('dashboard.game_type.ultrabullet'),
      'bullet': t('dashboard.game_type.bullet'),
      'blitz': t('dashboard.game_type.blitz'),
      'rapid': t('dashboard.game_type.rapid'),
      'classical': t('dashboard.game_type.classical'),
      'correspondence': t('dashboard.game_type.correspondence'),
      'unknown': t('dashboard.game_type.unknown')
    };

    if (gameTypeData.total_blunders > 0 && gameTypeData.by_game_type.length > 0) {
      gameTypeBarContainer.style.display = 'block';

      gameTypeBar.innerHTML = gameTypeData.by_game_type
        .filter(g => g.percentage > 0)
        .map(g => `<div class="game-type-bar-segment ${g.game_type}" style="flex: ${g.percentage}">${g.percentage > 8 ? g.percentage + '%' : ''}</div>`)
        .join('');

      const usedTypes = gameTypeData.by_game_type.filter(g => g.count > 0).map(g => g.game_type);
      gameTypeLegend.innerHTML = usedTypes.map(type => `
        <div class="game-type-legend-item">
          <span class="game-type-legend-color ${type}"></span>
          <span>${gameTypeLabels[type] || type}</span>
        </div>
      `).join('');

      gameTypeBreakdown.innerHTML = gameTypeData.by_game_type
        .filter(g => g.count > 0)
        .map(g => `
          <div class="game-type-card ${g.game_type}">
            <div class="game-type-name">${gameTypeLabels[g.game_type] || g.game_type}</div>
            <div class="game-type-count">${g.count}</div>
            <div class="game-type-percent">${g.percentage}%</div>
          </div>
        `).join('');
    } else {
      gameTypeBarContainer.style.display = 'none';
      gameTypeBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">' + t('dashboard.chart.no_game_type_data') + '</div>';
    }

    // Blunders by ECO opening
    if (hasFeature('dashboard.opening_breakdown') && document.getElementById('ecoBreakdown')) {
    const ecoData = await client.stats.blundersByEco(dateAndGameTypeParams());

    const ecoBreakdown = document.getElementById('ecoBreakdown');

    if (ecoData.total_blunders > 0 && ecoData.by_opening.length > 0) {
      const grouped = groupOpeningsByBase(ecoData.by_opening);
      ecoBreakdown.innerHTML = `
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
      initOpeningGroupToggles(ecoBreakdown);
    } else {
      ecoBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">' + t('dashboard.chart.no_opening_data') + '</div>';
    }
    }

    // Blunders by difficulty
    if (hasFeature('dashboard.difficulty_breakdown') && document.getElementById('difficultyBreakdown')) {
      const diffData = await client.stats.blundersByDifficulty(dateAndGameTypeParams());

      const diffBreakdown = document.getElementById('difficultyBreakdown');
      const diffBarContainer = document.getElementById('difficultyBarContainer');
      const diffBar = document.getElementById('difficultyBar');
      const diffLegend = document.getElementById('difficultyLegend');

      const diffToClass = {
        easy: 'diff-easy',
        medium: 'diff-medium',
        hard: 'diff-hard',
        unscored: 'diff-unscored',
      };

      const diffLabels = {
        easy: t('dashboard.difficulty.easy'),
        medium: t('dashboard.difficulty.medium'),
        hard: t('dashboard.difficulty.hard'),
        unscored: t('dashboard.difficulty.unscored'),
      };

      if (diffData.total_blunders > 0 && diffData.by_difficulty.length > 0) {
        diffBarContainer.style.display = 'block';

        diffBar.innerHTML = diffData.by_difficulty
          .filter(d => d.percentage > 0)
          .map(d => {
            const cls = diffToClass[d.difficulty] || 'diff-unscored';
            return `<div class="difficulty-bar-segment ${cls}" style="flex: ${d.percentage}">${d.percentage > 8 ? d.percentage + '%' : ''}</div>`;
          })
          .join('');

        diffLegend.innerHTML = diffData.by_difficulty
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

        diffBreakdown.innerHTML = diffData.by_difficulty
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
      } else {
        diffBarContainer.style.display = 'none';
        diffBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">' + t('dashboard.chart.no_difficulty_data') + '</div>';
      }
    }

    // Blunders by tactical pattern
    if (hasFeature('dashboard.tactical_breakdown') && document.getElementById('tacticalBreakdown')) {
    const tacticalData = await client.stats.blundersByTacticalPattern(dateAndGameTypeParams());

    const tacticalBreakdown = document.getElementById('tacticalBreakdown');
    const tacticalBarContainer = document.getElementById('tacticalBarContainer');
    const tacticalBar = document.getElementById('tacticalBar');
    const tacticalLegend = document.getElementById('tacticalLegend');

    const patternToClass = {
      'Fork': 'fork',
      'Pin': 'pin',
      'Skewer': 'skewer',
      'Discovered Attack': 'discovered',
      'Discovered Check': 'discovered',
      'Double Check': 'discovered',
      'Hanging Piece': 'hanging',
      'Back Rank Threat': 'back_rank',
      'Trapped Piece': 'other',
      'None': 'other'
    };

    const patternLabels = {
      'Fork': t('dashboard.tactical.fork'),
      'Pin': t('dashboard.tactical.pin'),
      'Skewer': t('dashboard.tactical.skewer'),
      'Discovered Attack': t('dashboard.tactical.discovery'),
      'Discovered Check': t('dashboard.tactical.disc_check'),
      'Double Check': t('dashboard.tactical.double_check'),
      'Hanging Piece': t('dashboard.tactical.hanging'),
      'Back Rank Threat': t('dashboard.tactical.back_rank'),
      'Trapped Piece': t('dashboard.tactical.trapped'),
      'None': t('dashboard.tactical.other')
    };

    if (tacticalData.total_blunders > 0 && tacticalData.by_pattern.length > 0) {
      tacticalBarContainer.style.display = 'block';

      tacticalBar.innerHTML = tacticalData.by_pattern
        .filter(p => p.percentage > 0)
        .map(p => {
          const cls = patternToClass[p.pattern] || 'other';
          return `<div class="tactical-bar-segment ${cls}" style="flex: ${p.percentage}">${p.percentage > 8 ? p.percentage + '%' : ''}</div>`;
        })
        .join('');

      const uniqueClasses = [...new Set(tacticalData.by_pattern.map(p => patternToClass[p.pattern] || 'other'))];
      tacticalLegend.innerHTML = uniqueClasses.map(cls => {
        const label = Object.entries(patternToClass).find(([_k, v]) => v === cls)?.[0] || cls;
        return `
          <div class="tactical-legend-item">
            <span class="tactical-legend-color ${cls}"></span>
            <span>${patternLabels[label] || label}</span>
          </div>
        `;
      }).join('');

      tacticalBreakdown.innerHTML = tacticalData.by_pattern
        .filter(p => p.count > 0)
        .map(p => {
          const cls = patternToClass[p.pattern] || 'other';
          const label = patternLabels[p.pattern] || p.pattern;
          return `
            <div class="tactical-card ${cls}">
              <div class="tactical-name">${label}</div>
              <div class="tactical-count">${p.count}</div>
              <div class="tactical-percent">${p.percentage}%</div>
            </div>
          `;
        }).join('');
    } else {
      tacticalBarContainer.style.display = 'none';
      tacticalBreakdown.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--text-muted);">' + t('dashboard.chart.no_tactical_data') + '</div>';
    }
    }

    // Game breakdown
    const breakdown = await client.stats.gameBreakdown();

    const tbody = document.querySelector('#gameBreakdownTable tbody');
    tbody.innerHTML = '';
    (breakdown.items || []).forEach(row => {
      tbody.innerHTML += `
        <tr>
          <td>${row.source}</td>
          <td>${row.username}</td>
          <td>${row.total_games}</td>
          <td>${row.analyzed_games}</td>
          <td>${row.pending_games}</td>
        </tr>
      `;
    });

  } catch (err) {
    console.error('Failed to load stats:', err);
  }
}

async function loadDateChart() {
  if (!document.getElementById('dateChartContainer')) return;
  try {
    const data = await client.stats.gamesByDate(dateAndGameTypeParams());

    const container = document.getElementById('dateChartContainer');
    const emptyMsg = document.getElementById('dateChartEmpty');

    if (!data.items || data.items.length === 0) {
      container.style.display = 'none';
      emptyMsg.style.display = 'block';
      return;
    }

    container.style.display = 'block';
    emptyMsg.style.display = 'none';

    const labels = data.items.map(d => d.date);
    const gameCounts = data.items.map(d => d.game_count);
    const accuracies = data.items.map(d => d.avg_accuracy);

    if (dateChart) {
      dateChart.destroy();
    }

    const ctx = document.getElementById('dateChart').getContext('2d');
    dateChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: t('dashboard.chart.games_played'),
            data: gameCounts,
            backgroundColor: 'rgba(14, 165, 233, 0.7)',
            borderColor: 'rgba(14, 165, 233, 1)',
            borderWidth: 1,
            yAxisID: 'y',
            order: 2
          },
          {
            label: t('dashboard.chart.accuracy'),
            data: accuracies,
            type: 'line',
            borderColor: 'rgba(34, 197, 94, 1)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.3,
            pointRadius: 3,
            yAxisID: 'y1',
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                if (context.dataset.yAxisID === 'y1') {
                  return `${t('dashboard.chart.accuracy')}: ${context.raw.toFixed(1)}%`;
                }
                return `${context.dataset.label}: ${context.raw}`;
              }
            }
          }
        },
        scales: {
          x: {
            ticks: {
              maxRotation: 45,
              minRotation: 45,
              maxTicksLimit: 15
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: t('dashboard.chart.games_axis')
            },
            beginAtZero: true
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: t('dashboard.chart.accuracy_axis')
            },
            min: 0,
            max: 100,
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
  } catch (err) {
    console.error('Failed to load date chart:', err);
  }
}

async function loadHourChart() {
  if (!document.getElementById('hourChartContainer')) return;
  try {
    const data = await client.stats.gamesByHour(dateAndGameTypeParams());

    const container = document.getElementById('hourChartContainer');
    const emptyMsg = document.getElementById('hourChartEmpty');

    if (!data.items || data.items.length === 0) {
      container.style.display = 'none';
      emptyMsg.style.display = 'block';
      return;
    }

    container.style.display = 'block';
    emptyMsg.style.display = 'none';

    const hourMap = new Map(data.items.map(d => [d.hour, d]));
    const fullData = [];
    for (let h = 0; h < 24; h++) {
      if (hourMap.has(h)) {
        fullData.push(hourMap.get(h));
      } else {
        fullData.push({ hour: h, game_count: 0, avg_accuracy: 0 });
      }
    }

    const labels = fullData.map(d => `${d.hour.toString().padStart(2, '0')}:00`);
    const gameCounts = fullData.map(d => d.game_count);
    const accuracies = fullData.map(d => d.avg_accuracy);

    if (hourChart) {
      hourChart.destroy();
    }

    const ctx = document.getElementById('hourChart').getContext('2d');
    hourChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: t('dashboard.chart.games_played'),
            data: gameCounts,
            backgroundColor: 'rgba(139, 92, 246, 0.7)',
            borderColor: 'rgba(139, 92, 246, 1)',
            borderWidth: 1,
            yAxisID: 'y',
            order: 2
          },
          {
            label: t('dashboard.chart.accuracy'),
            data: accuracies,
            type: 'line',
            borderColor: 'rgba(34, 197, 94, 1)',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            borderWidth: 2,
            fill: false,
            tension: 0.3,
            pointRadius: 3,
            yAxisID: 'y1',
            order: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false
        },
        plugins: {
          legend: {
            position: 'top'
          },
          tooltip: {
            callbacks: {
              label: function(context) {
                if (context.dataset.yAxisID === 'y1') {
                  return `${t('dashboard.chart.accuracy')}: ${context.raw.toFixed(1)}%`;
                }
                return `${context.dataset.label}: ${context.raw}`;
              }
            }
          }
        },
        scales: {
          x: {
            title: {
              display: true,
              text: t('dashboard.chart.hour_axis')
            }
          },
          y: {
            type: 'linear',
            display: true,
            position: 'left',
            title: {
              display: true,
              text: t('dashboard.chart.games_axis')
            },
            beginAtZero: true
          },
          y1: {
            type: 'linear',
            display: true,
            position: 'right',
            title: {
              display: true,
              text: t('dashboard.chart.accuracy_axis')
            },
            min: 0,
            max: 100,
            grid: {
              drawOnChartArea: false
            }
          }
        }
      }
    });
  } catch (err) {
    console.error('Failed to load hour chart:', err);
  }
}

async function retryAnalysis() {
  try {
    await client.analysis.start();
    loadStats();
  } catch (err) {
    console.error('Failed to retry analysis:', err);
    alert('Failed to start analysis: ' + err.message);
  }
}

// Load game type filters from localStorage
currentGameTypeFilters = gameTypeFilter.load();

// Add event listeners for game type filter checkboxes
document.querySelectorAll('.game-type-filter').forEach(checkbox => {
  checkbox.addEventListener('change', () => {
    currentGameTypeFilters = gameTypeFilter.save();
    loadStats();
  });
});

// Load stats on page load (after loading configured usernames)
loadConfiguredUsernames().then((usernames) => {
  configuredUsernames = usernames;
  loadStats();
});

if (hasFeature('dashboard.heatmap')) {
  loadHeatmap('activityHeatmap');
}

// WebSocket
wsClient.connect();
wsClient.subscribe(['stats.updated', 'job.completed', 'job.progress_updated', 'job.status_changed']);

wsClient.on('stats.updated', () => loadStats());
wsClient.on('job.completed', () => loadStats());
wsClient.on('job.progress_updated', () => loadStats());
wsClient.on('job.status_changed', () => loadStats());

// Wire up date filter buttons
document.getElementById('applyDateBtn').addEventListener('click', applyDateFilter);
document.getElementById('clearDateBtn').addEventListener('click', clearDateFilter);
document.querySelectorAll('.filter-presets button[data-preset]').forEach(btn => {
  btn.addEventListener('click', () => setPreset(btn.dataset.preset));
});

// Difficulty help modal
const diffHelpBtn = document.getElementById('difficultyHelpBtn');
const diffHelpOverlay = document.getElementById('difficultyHelpOverlay');
const diffHelpClose = document.getElementById('difficultyHelpClose');

if (diffHelpBtn && diffHelpOverlay) {
  diffHelpBtn.addEventListener('click', () => diffHelpOverlay.classList.add('visible'));
  diffHelpClose.addEventListener('click', () => diffHelpOverlay.classList.remove('visible'));
  diffHelpOverlay.addEventListener('click', (e) => {
    if (e.target === diffHelpOverlay) diffHelpOverlay.classList.remove('visible');
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && diffHelpOverlay.classList.contains('visible')) {
      diffHelpOverlay.classList.remove('visible');
    }
  });
}
