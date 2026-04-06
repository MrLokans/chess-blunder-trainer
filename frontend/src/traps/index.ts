import { client } from '../shared/api';
import { initDropdowns } from '../shared/dropdown';
import SequencePlayer from '../shared/sequence-player';

interface TrapStat {
  trap_id: string;
  name: string;
  category: string;
  entered: number;
  sprung: number;
  executed: number;
  last_seen?: string;
}

interface TrapSummary {
  total_sprung: number;
  total_entered: number;
  total_executed: number;
  games_with_traps: number;
  top_traps?: Array<{ trap_id: string; count: number }>;
}

interface TrapCatalogEntry {
  id: string;
  name: string;
}

interface TrapDetail {
  name: string;
  victim_side: string;
  trap_san?: string[][];
  refutation_san?: string[];
  mistake_san?: string;
  refutation_note?: string;
  refutation_move?: string;
  recognition_tip?: string;
}

interface TrapHistory {
  white: string;
  black: string;
  result: string;
  date?: string;
  game_url?: string;
  match_type: string;
}

let trapStats: TrapStat[] = [];
const trapCatalog: Record<string, TrapCatalogEntry> = {};
let activePlayer: SequencePlayer | null = null;

async function loadData(): Promise<void> {
  const [statsResp, catalogResp] = await Promise.all([
    client.traps.stats() as Promise<{ stats?: TrapStat[]; summary?: TrapSummary }>,
    client.traps.catalog() as Promise<TrapCatalogEntry[]>,
  ]);

  trapStats = statsResp.stats || [];
  const summary = statsResp.summary || {} as TrapSummary;

  catalogResp.forEach(c => { trapCatalog[c.id] = c; });

  renderSummary(summary);
  renderTable(trapStats);
}

function renderSummary(summary: TrapSummary): void {
  const el = document.getElementById('trapsSummary');
  if (!el) return;
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

function renderTable(stats: TrapStat[]): void {
  const tbody = document.getElementById('trapsTableBody');
  if (!tbody) return;
  const filterEl = document.getElementById('trapCategoryFilter') as HTMLSelectElement | null;
  const filter = filterEl?.value ?? 'all';

  const filtered = filter === 'all' ? stats : stats.filter(s => s.category === filter);

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="no-data">${t('traps.no_data')}</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(s => `
    <tr data-trap-id="${s.trap_id}">
      <td>${s.name}</td>
      <td><span class="category-badge">${t('traps.category.' + s.category) || s.category}</span></td>
      <td class="count-entered">${s.entered}</td>
      <td class="count-sprung">${s.sprung}</td>
      <td class="count-executed">${s.executed}</td>
      <td>${s.last_seen ? formatDate(s.last_seen, { year: 'numeric', month: '2-digit', day: '2-digit' }) : '-'}</td>
    </tr>
  `).join('');

  tbody.querySelectorAll<HTMLElement>('tr[data-trap-id]').forEach(row => {
    row.addEventListener('click', () => openDetail(row.dataset.trapId!));
  });
}

function destroyPlayer(): void {
  if (activePlayer) {
    activePlayer.destroy();
    activePlayer = null;
  }
}

function initPlayer(trap: TrapDetail): void {
  destroyPlayer();

  const trapMoves = trap.trap_san?.[0] || [];
  const playerOrientation = trap.victim_side === 'black' ? 'black' : 'white';
  const playerEl = document.getElementById('trapSequencePlayer');
  if (!playerEl) return;

  activePlayer = new SequencePlayer(playerEl, trapMoves, { orientation: playerOrientation });

  const trapTab = document.getElementById('trapTabTrap');
  const refTab = document.getElementById('trapTabRefutation');
  if (!trapTab || !refTab) return;

  trapTab.classList.add('active');
  refTab.classList.remove('active');

  trapTab.onclick = () => {
    if (trapTab.classList.contains('active')) return;
    trapTab.classList.add('active');
    refTab.classList.remove('active');
    activePlayer!.setMoves(trapMoves, { orientation: playerOrientation });
  };

  refTab.onclick = () => {
    if (refTab.classList.contains('active')) return;
    refTab.classList.add('active');
    trapTab.classList.remove('active');
    activePlayer!.setMoves(trap.refutation_san || [], { orientation: playerOrientation });
  };
}

async function openDetail(trapId: string): Promise<void> {
  const panel = document.getElementById('trapDetailPanel');
  panel?.classList.remove('hidden');

  const data = await client.traps.detail(trapId) as { trap: TrapDetail | null; history?: TrapHistory[] };
  const trap = data.trap;
  const history = data.history || [];

  const nameEl = document.getElementById('trapDetailName');
  if (nameEl) nameEl.textContent = trap ? trap.name : trapId;

  const mistakeEl = document.getElementById('trapMistakeInfo');
  if (mistakeEl) mistakeEl.textContent = trap ? `${t('traps.mistake')}: ${trap.mistake_san}` : '';
  const refNoteEl = document.getElementById('trapRefutationInfo');
  if (refNoteEl) refNoteEl.textContent = trap ? (trap.refutation_note ?? '') : '';
  const refMoveEl = document.getElementById('trapRefutationMove');
  if (refMoveEl) refMoveEl.textContent = trap ? `${t('traps.refutation')}: ${trap.refutation_move}` : '';
  const tipEl = document.getElementById('trapRecognitionTip');
  if (tipEl) tipEl.textContent = trap ? (trap.recognition_tip ?? '') : '';

  if (trap) {
    initPlayer(trap);
  }

  const gamesEl = document.getElementById('trapGamesList');
  if (!gamesEl) return;
  if (history.length === 0) {
    gamesEl.innerHTML = `<p>${t('traps.no_games')}</p>`;
  } else {
    gamesEl.innerHTML = history.map(g => {
      const typeClass = `match-type-${g.match_type}`;
      const label = `${g.white} vs ${g.black} (${g.result}) \u2014 ${g.date || ''}`;
      const gameLink = g.game_url
        ? `<a href="${g.game_url}" target="_blank" rel="noopener noreferrer">${label}</a>`
        : label;
      return `<div class="trap-game-item">
        <span class="${typeClass}">${g.match_type}</span>
        ${gameLink}
      </div>`;
    }).join('');
  }

  panel?.scrollIntoView({ behavior: 'smooth' });
}

document.addEventListener('DOMContentLoaded', () => {
  initDropdowns();
  loadData().catch(err => {
    console.error('Failed to load trap data:', err);
    const summary = document.getElementById('trapsSummary');
    if (summary) summary.innerHTML = `<p class="error">${t('common.error')}</p>`;
  });

  document.getElementById('trapCategoryFilter')?.addEventListener('change', () => {
    renderTable(trapStats);
  });

  document.getElementById('trapDetailClose')?.addEventListener('click', () => {
    destroyPlayer();
    document.getElementById('trapDetailPanel')?.classList.add('hidden');
  });
});
