import { useState, useEffect } from 'preact/hooks';
import { client } from '../shared/api';
import { useFeature } from '../hooks/useFeature';

const PHASE_KEYS: Record<number, string> = {
  0: 'chess.phase.opening',
  1: 'chess.phase.middlegame',
  2: 'chess.phase.endgame',
};

interface StarredItem {
  game_id: string;
  ply: number;
  san?: string;
  date?: string;
  white?: string;
  black?: string;
  cp_loss?: number | null;
  game_phase?: number;
  note?: string;
}

export function StarredApp() {
  const [items, setItems] = useState<StarredItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasGameReview = useFeature('page.game_review');

  useEffect(() => {
    void (async () => {
      try {
        const data = await client.starred.list<StarredItem>({ limit: 200 });
        setItems(data.items ?? []);
      } catch (err) {
        console.error('Failed to load starred puzzles:', err);
        setError(err instanceof Error ? err.message : String(err));
      }
    })();
  }, []);

  const handleUnstar = async (item: StarredItem) => {
    try {
      await client.starred.unstar(item.game_id, item.ply);
      setItems(prev => prev ? prev.filter(i => !(i.game_id === item.game_id && i.ply === item.ply)) : prev);
    } catch (err) {
      console.error('Failed to unstar:', err);
    }
  };

  if (error) {
    return <div class="error-message">{t('common.error')}: {error}</div>;
  }

  if (items === null) {
    return <p class="loading">{t('common.loading')}</p>;
  }

  if (items.length === 0) {
    return (
      <div class="empty-state">
        <p>{t('starred.empty')}</p>
      </div>
    );
  }

  return (
    <div class="starred-list">
      <table class="starred-table">
        <thead>
          <tr>
            <th>{t('starred.col.date')}</th>
            <th>{t('starred.col.players')}</th>
            <th>{t('starred.col.move')}</th>
            <th>{t('starred.col.eval_swing')}</th>
            <th>{t('starred.col.phase')}</th>
            <th>{t('starred.col.note')}</th>
            {hasGameReview && <th></th>}
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map(item => (
            <tr key={`${item.game_id}-${item.ply}`}>
              <td>
                {item.date
                  ? formatDate(item.date, { year: 'numeric', month: '2-digit', day: '2-digit' })
                  : '\u2014'}
              </td>
              <td>
                {item.white && item.black
                  ? `${item.white} vs ${item.black}`
                  : '\u2014'}
              </td>
              <td>
                <a
                  class="puzzle-link"
                  href={`/?game_id=${encodeURIComponent(item.game_id)}&ply=${item.ply}`}
                >
                  {item.san ?? `ply ${item.ply}`}
                </a>
              </td>
              <td class="eval-swing">
                {item.cp_loss != null
                  ? `-${(item.cp_loss / 100).toFixed(1)}`
                  : '\u2014'}
              </td>
              <td>{PHASE_KEYS[item.game_phase ?? -1] ? t(PHASE_KEYS[item.game_phase ?? -1]!) : '\u2014'}</td>
              <td class="note-text" title={item.note ?? ''}>{item.note ?? ''}</td>
              {hasGameReview && (
                <td>
                  <a
                    class="puzzle-link"
                    href={`/game/${encodeURIComponent(item.game_id)}?ply=${item.ply}`}
                  >
                    {t('game_review.link.review_game')}
                  </a>
                </td>
              )}
              <td>
                <button
                  class="unstar-btn"
                  title={t('starred.unstar')}
                  onClick={() => { void handleUnstar(item); }}
                >
                  &#9733;
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
