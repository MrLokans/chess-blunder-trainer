import { useState, useEffect, useRef } from 'preact/hooks';
import { client } from '../shared/api';
import { useAsyncData } from '../hooks/useAsyncData';
import { AsyncBoundary } from '../components/feedback/AsyncBoundary';
import { EmptyState } from '../components/layout/EmptyState';
import { Dropdown } from '../components/primitives/Dropdown';
import { PageHeader } from '../components/layout/PageHeader';
import { Tabs, type TabDescriptor } from '../components/layout/Tabs';
import SequencePlayer from '../shared/sequence-player';
import type {
  TrapStat, TrapSummary, TrapCatalogEntry,
  TrapDetail, TrapDetailData,
} from '../types/api';

type TabKey = 'trap' | 'refutation';

const LINE_TABS: TabDescriptor<TabKey>[] = [
  { key: 'trap', label: 'traps.tab.trap_line' },
  { key: 'refutation', label: 'traps.tab.refutation_line' },
];

interface TrapsData {
  stats: TrapStat[];
  summary: TrapSummary;
  catalog: Record<string, TrapCatalogEntry>;
}

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
  const [activeTab, setActiveTab] = useState<TabKey>('trap');

  const state = useAsyncData<TrapDetailData>(
    () => client.traps.detail(trapId),
    [trapId],
  );

  useEffect(() => {
    setActiveTab('trap');
  }, [trapId]);

  useEffect(() => {
    const panel = document.getElementById('trapDetailPanel');
    if (panel && typeof panel.scrollIntoView === 'function') {
      panel.scrollIntoView({ behavior: 'smooth' });
    }
  }, [trapId]);

  const name = catalog[trapId]?.name ?? trapId;
  const headerTitle = state.data?.trap?.name ?? name;

  return (
    <div class="trap-detail-panel" id="trapDetailPanel">
      <button class="trap-detail-close" onClick={onClose}>&times;</button>
      <PageHeader title={headerTitle} />

      <AsyncBoundary
        state={state}
        isEmpty={(data) => data.trap === null}
        empty={<EmptyState title={name} message={t('traps.no_data')} />}
      >
        {(data) => <TrapDetailView data={data} activeTab={activeTab} onChangeTab={setActiveTab} />}
      </AsyncBoundary>
    </div>
  );
}

interface TrapDetailViewProps {
  data: TrapDetailData;
  activeTab: TabKey;
  onChangeTab: (tab: TabKey) => void;
}

function TrapDetailView({ data, activeTab, onChangeTab }: TrapDetailViewProps) {
  const trap = data.trap;
  if (trap === null) return null;
  const history = data.history;

  return (
    <div class="trap-detail-grid">
      <div class="trap-detail-section trap-board-section">
        <Tabs<TabKey>
          tabs={LINE_TABS.map(tab => ({ ...tab, label: t(tab.label) }))}
          value={activeTab}
          onChange={onChangeTab}
        >
          <BoardPlayer trap={trap} activeTab={activeTab} />
        </Tabs>
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
                const label = `${g.white} vs ${g.black} (${g.result}) — ${g.date ?? ''}`;
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

interface TrapsViewProps {
  data: TrapsData;
}

function TrapsView({ data }: TrapsViewProps) {
  const { stats, summary, catalog } = data;
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [selectedTrapId, setSelectedTrapId] = useState<string | null>(null);

  const categoryOptions = CATEGORIES.map(cat => ({
    value: cat,
    label: t(`traps.category.${cat}`),
  }));

  const filteredStats = categoryFilter === 'all'
    ? stats
    : stats.filter(s => s.category === categoryFilter);

  return (
    <>
      <Summary summary={summary} catalog={catalog} />

      <div class="traps-filter">
        <label>{t('traps.filter_category')}</label>
        <Dropdown
          options={categoryOptions}
          value={categoryFilter}
          onChange={setCategoryFilter}
        />
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
            {filteredStats.length === 0 ? (
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

export function TrapsApp() {
  const state = useAsyncData<TrapsData>(
    async () => {
      const [statsResp, catalogResp] = await Promise.all([
        client.traps.stats(),
        client.traps.catalog(),
      ]);

      const catalogMap: Record<string, TrapCatalogEntry> = {};
      catalogResp.forEach(c => { catalogMap[c.id] = c; });

      return { stats: statsResp.stats, summary: statsResp.summary, catalog: catalogMap };
    },
    [],
  );

  return (
    <AsyncBoundary
      state={state}
      isEmpty={(data) => data.stats.length === 0}
      empty={<EmptyState title={t('traps.title')} message={t('traps.no_data')} />}
    >
      {(data) => <TrapsView data={data} />}
    </AsyncBoundary>
  );
}
