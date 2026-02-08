import { client } from './api.js';

let trapStats = [];
const trapCatalog = {};

async function loadData() {
  const [statsResp, catalogResp] = await Promise.all([
    client.traps.stats(),
    client.traps.catalog(),
  ]);

  trapStats = statsResp.stats || [];
  const summary = statsResp.summary || {};

  catalogResp.forEach(c => { trapCatalog[c.id] = c; });

  renderSummary(summary);
  renderTable(trapStats);
}

function renderSummary(summary) {
  const el = document.getElementById('trapsSummary');
  if (!summary || summary.total_sprung === 0 && summary.total_entered === 0) {
    el.innerHTML = `<p>${t('traps.no_data')}</p>`;
    return;
  }

  let topHtml = '';
  if (summary.top_traps && summary.top_traps.length > 0) {
    const tags = summary.top_traps.map(tt => {
      const name = trapCatalog[tt.trap_id]?.name || tt.trap_id;
      return `<span class="trap-tag">${name} (${tt.count})</span>`;
    }).join('');
    topHtml = `<div class="top-traps"><strong>${t('traps.most_common')}:</strong> ${tags}</div>`;
  }

  el.innerHTML = `
    <div class="summary-stats">
      <div class="stat-item">
        <div class="stat-value">${summary.total_sprung}</div>
        <div class="stat-label">${t('traps.times_fell')}</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${summary.total_entered}</div>
        <div class="stat-label">${t('traps.times_entered')}</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${summary.total_executed}</div>
        <div class="stat-label">${t('traps.times_executed')}</div>
      </div>
      <div class="stat-item">
        <div class="stat-value">${summary.games_with_traps}</div>
        <div class="stat-label">${t('traps.games_involved')}</div>
      </div>
    </div>
    ${topHtml}
  `;
}

function renderTable(stats) {
  const tbody = document.getElementById('trapsTableBody');
  const filter = document.getElementById('trapCategoryFilter').value;

  const filtered = filter === 'all' ? stats : stats.filter(s => s.category === filter);

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="no-data">${t('traps.no_data')}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => `
    <tr data-trap-id="${s.trap_id}">
      <td>${s.name}</td>
      <td><span class="category-badge">${s.category}</span></td>
      <td class="count-entered">${s.entered}</td>
      <td class="count-sprung">${s.sprung}</td>
      <td class="count-executed">${s.executed}</td>
      <td>${s.last_seen ? new Date(s.last_seen).toLocaleDateString() : '-'}</td>
    </tr>
  `).join('');

  tbody.querySelectorAll('tr[data-trap-id]').forEach(row => {
    row.addEventListener('click', () => openDetail(row.dataset.trapId));
  });
}

async function openDetail(trapId) {
  const panel = document.getElementById('trapDetailPanel');
  panel.style.display = 'block';

  const data = await client.traps.detail(trapId);
  const trap = data.trap;
  const history = data.history || [];

  document.getElementById('trapDetailName').textContent = trap ? trap.name : trapId;

  document.getElementById('trapMistakeInfo').textContent =
    trap ? `${t('traps.mistake_at_ply')} ${trap.mistake_ply}: ${trap.mistake_san}` : '';
  document.getElementById('trapRefutationInfo').textContent =
    trap ? trap.refutation_note : '';
  document.getElementById('trapRefutationMove').textContent =
    trap ? `${t('traps.refutation')}: ${trap.refutation_move}` : '';
  document.getElementById('trapRecognitionTip').textContent =
    trap ? trap.recognition_tip : '';

  const gamesEl = document.getElementById('trapGamesList');
  if (history.length === 0) {
    gamesEl.innerHTML = `<p>${t('traps.no_games')}</p>`;
  } else {
    gamesEl.innerHTML = history.map(g => {
      const typeClass = `match-type-${g.match_type}`;
      return `<div class="trap-game-item">
        <span class="${typeClass}">${g.match_type}</span>
        ${g.white} vs ${g.black} (${g.result}) — ${g.date || ''}
      </div>`;
    }).join('');
  }

  panel.scrollIntoView({ behavior: 'smooth' });
}

document.addEventListener('DOMContentLoaded', () => {
  loadData().catch(err => {
    console.error('Failed to load trap data:', err);
    document.getElementById('trapsSummary').innerHTML =
      `<p class="error">${t('common.error')}</p>`;
  });

  document.getElementById('trapCategoryFilter').addEventListener('change', () => {
    renderTable(trapStats);
  });

  document.getElementById('trapDetailClose').addEventListener('click', () => {
    document.getElementById('trapDetailPanel').style.display = 'none';
  });
});
