import { client } from './api.js';
import { hasFeature } from './features.js';

const PHASE_LABELS = {
  0: 'Opening',
  1: 'Middlegame',
  2: 'Endgame',
};

const t = window.t || ((key) => key);

async function loadStarred() {
  const content = document.getElementById('starredContent');
  const emptyEl = document.getElementById('starredEmpty');
  const listEl = document.getElementById('starredList');
  const tbody = document.getElementById('starredTableBody');

  try {
    const data = await client.starred.list({ limit: 200 });

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
        : '—';
      tr.appendChild(dateCell);

      const playersCell = document.createElement('td');
      playersCell.textContent = (item.white && item.black)
        ? `${item.white} vs ${item.black}`
        : '—';
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
        evalCell.textContent = '—';
      }
      tr.appendChild(evalCell);

      const phaseCell = document.createElement('td');
      phaseCell.textContent = PHASE_LABELS[item.game_phase] || '—';
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
      unstarBtn.textContent = '★';
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
    content.innerHTML = '<p class="error">Failed to load starred puzzles</p>';
  }
}

loadStarred();
