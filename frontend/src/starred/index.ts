import { client } from '../shared/api';
import { hasFeature } from '../shared/features';

const PHASE_LABELS: Record<number, string> = {
  0: 'Opening',
  1: 'Middlegame',
  2: 'Endgame',
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

async function loadStarred(): Promise<void> {
  const content = document.getElementById('starredContent');
  const emptyEl = document.getElementById('starredEmpty');
  const listEl = document.getElementById('starredList');
  const tbody = document.getElementById('starredTableBody');

  if (!content || !emptyEl || !listEl || !tbody) return;

  try {
    const data = await client.starred.list({ limit: 200 }) as { items?: StarredItem[] };

    content.classList.add('hidden');

    if (!data.items || data.items.length === 0) {
      emptyEl.classList.remove('hidden');
      listEl.classList.add('hidden');
      return;
    }

    emptyEl.classList.add('hidden');
    listEl.classList.remove('hidden');
    tbody.innerHTML = '';

    for (const item of data.items) {
      const tr = document.createElement('tr');

      const dateCell = document.createElement('td');
      dateCell.textContent = item.date
        ? formatDate(item.date, { year: 'numeric', month: '2-digit', day: '2-digit' })
        : '\u2014';
      tr.appendChild(dateCell);

      const playersCell = document.createElement('td');
      playersCell.textContent = (item.white && item.black)
        ? `${item.white} vs ${item.black}`
        : '\u2014';
      tr.appendChild(playersCell);

      const moveCell = document.createElement('td');
      const link = document.createElement('a');
      link.href = `/?game_id=${encodeURIComponent(item.game_id)}&ply=${item.ply}`;
      link.className = 'puzzle-link';
      link.textContent = item.san || `ply ${item.ply}`;
      moveCell.appendChild(link);
      tr.appendChild(moveCell);

      const evalCell = document.createElement('td');
      evalCell.className = 'eval-swing';
      if (item.cp_loss != null) {
        evalCell.textContent = `-${(item.cp_loss / 100).toFixed(1)}`;
      } else {
        evalCell.textContent = '\u2014';
      }
      tr.appendChild(evalCell);

      const phaseCell = document.createElement('td');
      phaseCell.textContent = PHASE_LABELS[item.game_phase ?? -1] || '\u2014';
      tr.appendChild(phaseCell);

      const noteCell = document.createElement('td');
      noteCell.className = 'note-text';
      noteCell.textContent = item.note || '';
      noteCell.title = item.note || '';
      tr.appendChild(noteCell);

      if (hasFeature('page.game_review')) {
        const reviewCell = document.createElement('td');
        const reviewLink = document.createElement('a');
        reviewLink.href = `/game/${encodeURIComponent(item.game_id)}?ply=${item.ply}`;
        reviewLink.className = 'puzzle-link';
        reviewLink.textContent = t('game_review.link.review_game');
        reviewCell.appendChild(reviewLink);
        tr.appendChild(reviewCell);
      }

      const actionCell = document.createElement('td');
      const unstarBtn = document.createElement('button');
      unstarBtn.className = 'unstar-btn';
      unstarBtn.textContent = '\u2605';
      unstarBtn.title = t('starred.unstar');
      unstarBtn.addEventListener('click', async () => {
        try {
          await client.starred.unstar(item.game_id, item.ply);
          tr.remove();
          const remaining = tbody.querySelectorAll('tr');
          if (remaining.length === 0) {
            listEl.classList.add('hidden');
            emptyEl.classList.remove('hidden');
          }
        } catch (e) {
          console.error('Failed to unstar:', e);
        }
      });
      actionCell.appendChild(unstarBtn);
      tr.appendChild(actionCell);

      tbody.appendChild(tr);
    }
  } catch (err) {
    console.error('Failed to load starred puzzles:', err);
    if (content) content.innerHTML = '<p class="error">Failed to load starred puzzles</p>';
  }
}

loadStarred();
