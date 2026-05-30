import { useState, useEffect } from 'preact/hooks';
import { client } from '../shared/api';
import { useFeature } from '../hooks/useFeature';
import { useAsyncData } from '../hooks/useAsyncData';
import { AsyncBoundary } from '../components/AsyncBoundary';
import { EmptyState } from '../components/EmptyState';
import { DataTable } from '../components/DataTable';
import type { Column } from '../components/DataTable';
import type { StarredItem } from '../types/api';

const PHASE_KEYS: Record<number, string> = {
  0: 'chess.phase.opening',
  1: 'chess.phase.middlegame',
  2: 'chess.phase.endgame',
};

export function StarredApp() {
  const hasGameReview = useFeature('page.game_review');
  const state = useAsyncData<StarredItem[]>(
    async () => (await client.starred.list({ limit: 200 })).items,
    [],
  );
  // useAsyncData owns the fetch; unstar is a local mutation, so we mirror the
  // fetched list into state the handler can splice. Empty detection then
  // follows the live list (unstarring the last item shows the empty slot).
  const [items, setItems] = useState<StarredItem[] | null>(null);

  useEffect(() => {
    setItems(state.data);
  }, [state.data]);

  const handleUnstar = async (item: StarredItem) => {
    try {
      await client.starred.unstar(item.game_id, item.ply);
      setItems(prev => prev ? prev.filter(i => !(i.game_id === item.game_id && i.ply === item.ply)) : prev);
    } catch (err) {
      console.error('Failed to unstar:', err);
    }
  };

  return (
    <AsyncBoundary
      state={{ loading: state.loading, error: state.error, data: items }}
      empty={<EmptyState title={t('starred.title')} message={t('starred.empty')} />}
    >
      {(rows) => renderTable(rows, hasGameReview, handleUnstar)}
    </AsyncBoundary>
  );
}

function phaseLabel(phase: number | null | undefined): string | null {
  const key = PHASE_KEYS[phase ?? -1];
  return key ? t(key) : null;
}

interface StarredRow {
  date: string | null;
  players: string | null;
  eval_swing: string | null;
  phase: string | null;
  item: StarredItem;
}

function toRow(item: StarredItem): StarredRow {
  return {
    date: item.date
      ? formatDate(item.date, { year: 'numeric', month: '2-digit', day: '2-digit' })
      : null,
    players: item.white && item.black ? `${item.white} vs ${item.black}` : null,
    eval_swing: item.cp_loss != null ? `-${(item.cp_loss / 100).toFixed(1)}` : null,
    phase: phaseLabel(item.game_phase),
    item,
  };
}

function renderTable(
  items: StarredItem[],
  hasGameReview: boolean,
  handleUnstar: (item: StarredItem) => Promise<void>,
) {
  const columns: Column<StarredRow>[] = [
    { key: 'date', header: t('starred.col.date') },
    { key: 'players', header: t('starred.col.players') },
    {
      key: 'move',
      header: t('starred.col.move'),
      render: ({ item }) => (
        <a
          class="puzzle-link"
          href={`/?game_id=${encodeURIComponent(item.game_id)}&ply=${String(item.ply)}`}
        >
          {item.san ?? `ply ${String(item.ply)}`}
        </a>
      ),
    },
    { key: 'eval_swing', header: t('starred.col.eval_swing'), className: 'eval-swing' },
    { key: 'phase', header: t('starred.col.phase') },
    {
      key: 'note',
      header: t('starred.col.note'),
      className: 'note-text',
      render: ({ item }) => <span title={item.note ?? ''}>{item.note ?? ''}</span>,
    },
  ];

  if (hasGameReview) {
    columns.push({
      key: 'review',
      header: '',
      render: ({ item }) => (
        <a
          class="puzzle-link"
          href={`/game/${encodeURIComponent(item.game_id)}?ply=${String(item.ply)}`}
        >
          {t('game_review.link.review_game')}
        </a>
      ),
    });
  }

  columns.push({
    key: 'unstar',
    header: '',
    render: ({ item }) => (
      <button
        class="unstar-btn"
        title={t('starred.unstar')}
        onClick={() => { void handleUnstar(item); }}
      >
        &#9733;
      </button>
    ),
  });

  return (
    <div class="starred-list">
      <DataTable
        className="starred-table"
        columns={columns}
        rows={items.map(toRow)}
        rowKey={({ item }) => `${item.game_id}-${String(item.ply)}`}
      />
    </div>
  );
}
