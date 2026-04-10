import { useState, useEffect, useRef, useCallback } from 'preact/hooks';
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

interface TrapDetailData {
  trap: TrapDetail | null;
  history: TrapHistory[];
}

type TabKey = 'trap' | 'refutation';

interface BoardPlayerProps {
  trap: TrapDetail;
  activeTab: TabKey;
}

function BoardPlayer({ trap, activeTab }: BoardPlayerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const playerRef = useRef<SequencePlayer | null>(null);

  const trapMoves = trap.trap_san?.[0] ?? [];
  const refutationMoves = trap.refutation_san ?? [];
  const orientation = trap.victim_side === 'black' ? 'black' : 'white';

  useEffect(() => {
    if (!containerRef.current) return;

    const moves = activeTab === 'trap' ? trapMoves : refutationMoves;

    if (playerRef.current) {
      playerRef.current.setMoves(moves, { orientation });
    } else {
      playerRef.current = new SequencePlayer(containerRef.current, moves, { orientation });
    }

    return () => {
      if (playerRef.current) {
        playerRef.current.destroy();
        playerRef.current = null;
      }
    };
  }, [activeTab, trap]);

  return <div ref={containerRef} class="trap-board-container" />;
}

interface DetailPanelProps {
  trapId: string;
  catalog: Record<string, TrapCatalogEntry>;
  onClose: () => void;
}

function DetailPanel({ trapId, catalog, onClose }: DetailPanelProps) {
  const [detail, setDetail] = useState<TrapDetailData | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('trap');
  const [error, setError] = useState<string | null>(null);

  const name = catalog[trapId]?.name ?? trapId;

  useEffect(() => {
    setDetail(null);
    setError(null);
    setActiveTab('trap');

    client.traps.detail<{ trap: TrapDetail | null; history?: TrapHistory[] }>(trapId)
      .then(resp => {
        setDetail({ trap: resp.trap, history: resp.history ?? [] });
      })
      .catch((err: unknown) => {
        console.error('Failed to load trap detail:', err);
        setError(t('common.error'));
      });
  }, [trapId]);

  useEffect(() => {
    const panel = document.getElementById('trapDetailPanel');
    if (panel && typeof panel.scrollIntoView === 'function') {
      panel.scrollIntoView({ behavior: 'smooth' });
    }
  }, [trapId]);

  const trap = detail?.trap ?? null;
  const history = detail?.history ?? [];

  return (
    <div class="trap-detail-panel" id="trapDetailPanel">
      <button class="trap-detail-close" onClick={onClose}>&times;</button>
      <h2>{trap ? trap.name : name}</h2>

      {error && <p class="error">{error}</p>}

      {!detail && !error && <p class="loading">{t('common.loading')}</p>}

      {trap && (
        <div class="trap-detail-grid">
          <div class="trap-detail-section trap-board-section">
            <div class="sequence-player-tabs">
              <button
                class={`tab-btn${activeTab === 'trap' ? ' active' : ''}`}
                onClick={() => { setActiveTab('trap'); }}
              >
                {t('traps.tab.trap_line')}
              </button>
              <button
                class={`tab-btn${activeTab === 'refutation' ? ' active' : ''}`}
                onClick={() => { setActiveTab('refutation'); }}
              >
                {t('traps.tab.refutation_line')}
              </button>
            </div>
            <BoardPlayer trap={trap} activeTab={activeTab} />
          </div>

          <div class="trap-detail-info">
            <div class="trap-detail-section">
              <h3>{t('traps.the_mistake')}</h3>
              <p>{trap.mistake_san ? `${t('traps.mistake')}: ${trap.mistake_san}` : ''}</p>
            </div>
            <div class="trap-detail-section">
              <h3>{t('traps.refutation')}</h3>
              <p>{trap.refutation_note ?? ''}</p>
              <p class="trap-refutation-move">
                {trap.refutation_move ? `${t('traps.refutation')}: ${trap.refutation_move}` : ''}
              </p>
            </div>
            <div class="trap-detail-section">
              <h3>{t('traps.recognition_tip')}</h3>
              <p>{trap.recognition_tip ?? ''}</p>
            </div>
            <div class="trap-detail-section">
              <h3>{t('traps.your_games')}</h3>
              <div class="trap-games-list">
                {history.length === 0 ? (
                  <p>{t('traps.no_games')}</p>
                ) : (
                  history.map((g, i) => {
                    const label = `${g.white} vs ${g.black} (${g.result}) \u2014 ${g.date ?? ''}`;
                    return (
                      <div key={i} class="trap-game-item">
                        <span class={`match-type-${g.match_type}`}>{g.match_type}</span>
                        {g.game_url ? (
                          <a href={g.game_url} target="_blank" rel="noopener noreferrer">{label}</a>
                        ) : (
                          label
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

interface SummaryProps {
  summary: TrapSummary;
  catalog: Record<string, TrapCatalogEntry>;
}

function Summary({ summary, catalog }: SummaryProps) {
  const isEmpty = summary.total_sprung === 0 && summary.total_entered === 0;

  if (isEmpty) {
    return (
      <div class="traps-summary">
        <p>{t('traps.no_data')}</p>
      </div>
    );
  }

  return (
    <div class="traps-summary">
      <div class="summary-stats">
        <div class="stat-item">
          <div class="stat-value">{summary.total_sprung}</div>
          <div class="stat-label">{t('traps.times_fell')}</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{summary.total_entered}</div>
          <div class="stat-label">{t('traps.times_entered')}</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{summary.total_executed}</div>
          <div class="stat-label">{t('traps.times_executed')}</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{summary.games_with_traps}</div>
          <div class="stat-label">{t('traps.games_involved')}</div>
        </div>
      </div>
      {summary.top_traps && summary.top_traps.length > 0 && (
        <div class="top-traps">
          <strong>{t('traps.most_common')}:</strong>{' '}
          {summary.top_traps.map(tt => {
            const trapName = catalog[tt.trap_id]?.name ?? tt.trap_id;
            return <span key={tt.trap_id} class="trap-tag">{trapName} ({tt.count})</span>;
          })}
        </div>
      )}
    </div>
  );
}

const CATEGORIES = ['all', 'checkmate', 'attack', 'gambit_trap', 'piece_trap', 'pin_fork_trick'];

export function TrapsApp() {
  const [stats, setStats] = useState<TrapStat[] | null>(null);
  const [summary, setSummary] = useState<TrapSummary | null>(null);
  const [catalog, setCatalog] = useState<Record<string, TrapCatalogEntry>>({});
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [selectedTrapId, setSelectedTrapId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const filterRef = useRef<HTMLSelectElement>(null);

  const loadData = useCallback(async () => {
    try {
      const [statsResp, catalogResp] = await Promise.all([
        client.traps.stats<{ stats?: TrapStat[]; summary?: TrapSummary }>(),
        client.traps.catalog<TrapCatalogEntry>(),
      ]);

      const catalogMap: Record<string, TrapCatalogEntry> = {};
      catalogResp.forEach(c => { catalogMap[c.id] = c; });

      setStats(statsResp.stats ?? []);
      setSummary(statsResp.summary ?? { total_sprung: 0, total_entered: 0, total_executed: 0, games_with_traps: 0 });
      setCatalog(catalogMap);
    } catch (err) {
      console.error('Failed to load trap data:', err);
      setError(t('common.error'));
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  useEffect(() => {
    if (filterRef.current) {
      initDropdowns(filterRef.current.parentElement ?? undefined);
    }
  }, [stats]);

  const filteredStats = stats
    ? (categoryFilter === 'all' ? stats : stats.filter(s => s.category === categoryFilter))
    : [];

  return (
    <>
      {error && !stats && (
        <div class="traps-summary">
          <p class="error">{error}</p>
        </div>
      )}

      {!stats && !error && (
        <div class="traps-summary">
          <p class="loading">{t('common.loading')}</p>
        </div>
      )}

      {summary && stats && (
        <Summary summary={summary} catalog={catalog} />
      )}

      <div class="traps-filter">
        <label for="trapCategoryFilter">{t('traps.filter_category')}</label>
        <select
          id="trapCategoryFilter"
          ref={filterRef}
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.currentTarget.value); }}
        >
          {CATEGORIES.map(cat => (
            <option key={cat} value={cat}>{t(`traps.category.${cat}`)}</option>
          ))}
        </select>
      </div>

      <div class="traps-table-container">
        <table class="traps-table">
          <thead>
            <tr>
              <th>{t('traps.col_name')}</th>
              <th>{t('traps.col_category')}</th>
              <th>{t('traps.col_entered')}</th>
              <th>{t('traps.col_fell')}</th>
              <th>{t('traps.col_executed')}</th>
              <th>{t('traps.col_last_seen')}</th>
            </tr>
          </thead>
          <tbody>
            {!stats ? (
              <tr><td colspan={6} class="loading">{t('common.loading')}</td></tr>
            ) : filteredStats.length === 0 ? (
              <tr><td colspan={6} class="no-data">{t('traps.no_data')}</td></tr>
            ) : (
              filteredStats.map(s => (
                <tr
                  key={s.trap_id}
                  data-trap-id={s.trap_id}
                  onClick={() => { setSelectedTrapId(s.trap_id); }}
                  style="cursor: pointer"
                >
                  <td>{s.name}</td>
                  <td><span class="category-badge">{t(`traps.category.${s.category}`) || s.category}</span></td>
                  <td class="count-entered">{s.entered}</td>
                  <td class="count-sprung">{s.sprung}</td>
                  <td class="count-executed">{s.executed}</td>
                  <td>{s.last_seen ? formatDate(s.last_seen, { year: 'numeric', month: '2-digit', day: '2-digit' }) : '-'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {selectedTrapId && (
        <DetailPanel
          trapId={selectedTrapId}
          catalog={catalog}
          onClose={() => { setSelectedTrapId(null); }}
        />
      )}
    </>
  );
}
