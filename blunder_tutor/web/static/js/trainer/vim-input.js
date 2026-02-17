let overlay, field, errorEl, suggestionsEl;
let cfg = {};
let active = false;
let suggestions = [];
let selectedIndex = -1;

export function initVimInput({ getGame, getBoard, isInteractive, onMoveComplete }) {
  cfg = { getGame, getBoard, isInteractive, onMoveComplete };
  overlay = document.getElementById('vimInput');
  field = document.getElementById('vimInputField');
  errorEl = document.getElementById('vimInputError');
  suggestionsEl = document.getElementById('vimSuggestions');
  if (!overlay || !field) return;

  field.addEventListener('keydown', onKeyDown);
  field.addEventListener('input', onInput);
  overlay.addEventListener('animationend', () => overlay.classList.remove('shake'));
}

export function show() {
  if (!overlay || !cfg.isInteractive()) return;
  active = true;
  field.value = '';
  errorEl.classList.remove('visible');
  errorEl.textContent = '';
  clearSuggestions();
  overlay.classList.add('active');
  field.focus();
  updateSuggestions();
}

export function hide() {
  if (!overlay) return;
  active = false;
  clearSuggestions();
  overlay.classList.remove('active');
  field.blur();
}

export function isVimInputActive() {
  return active;
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.add('visible');
  overlay.classList.add('shake');
  field.select();
  setTimeout(() => errorEl.classList.remove('visible'), 1500);
}

function getLegalMoves() {
  const game = cfg.getGame();
  if (!game) return [];
  return game.moves();
}

function updateSuggestions() {
  const input = field.value.trim();
  const legal = getLegalMoves();

  if (!input) {
    suggestions = legal;
  } else {
    const lower = input.toLowerCase();
    suggestions = legal.filter(m => m.toLowerCase().startsWith(lower));
  }

  selectedIndex = -1;
  renderSuggestions();
}

function renderSuggestions() {
  if (!suggestionsEl) return;

  if (suggestions.length === 0 || (suggestions.length === 1 && suggestions[0] === field.value.trim())) {
    suggestionsEl.classList.remove('visible');
    suggestionsEl.innerHTML = '';
    return;
  }

  const maxVisible = 8;
  const visible = suggestions.slice(0, maxVisible);

  suggestionsEl.innerHTML = visible.map((move, i) => {
    const cls = i === selectedIndex ? 'vim-suggestion selected' : 'vim-suggestion';
    const input = field.value.trim();
    const matchLen = input.length;
    const matched = move.slice(0, matchLen);
    const rest = move.slice(matchLen);
    return `<span class="${cls}" data-index="${i}"><b>${matched}</b>${rest}</span>`;
  }).join('');

  if (suggestions.length > maxVisible) {
    suggestionsEl.innerHTML += `<span class="vim-suggestion more">+${suggestions.length - maxVisible}</span>`;
  }

  suggestionsEl.classList.add('visible');

  suggestionsEl.querySelectorAll('.vim-suggestion:not(.more)').forEach(el => {
    el.addEventListener('mousedown', (e) => {
      e.preventDefault();
      const idx = parseInt(el.dataset.index, 10);
      acceptSuggestion(idx);
    });
  });
}

function acceptSuggestion(index) {
  if (index >= 0 && index < suggestions.length) {
    field.value = suggestions[index];
    clearSuggestions();
    tryMove();
  }
}

function clearSuggestions() {
  suggestions = [];
  selectedIndex = -1;
  if (suggestionsEl) {
    suggestionsEl.classList.remove('visible');
    suggestionsEl.innerHTML = '';
  }
}

function onInput() {
  updateSuggestions();
}

function onKeyDown(e) {
  if (e.key === 'Escape') {
    e.preventDefault();
    e.stopPropagation();
    hide();
    return;
  }

  if (e.key === 'Tab') {
    e.preventDefault();
    e.stopPropagation();
    if (suggestions.length === 1) {
      acceptSuggestion(0);
      return;
    }
    if (suggestions.length > 0) {
      const newIndex = e.shiftKey
        ? (selectedIndex <= 0 ? suggestions.length - 1 : selectedIndex - 1)
        : (selectedIndex + 1) % suggestions.length;
      selectedIndex = Math.min(newIndex, 7);
      renderSuggestions();
    }
    return;
  }

  if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (suggestions.length > 0) {
      selectedIndex = selectedIndex <= 0 ? Math.min(suggestions.length, 8) - 1 : selectedIndex - 1;
      renderSuggestions();
    }
    return;
  }

  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (suggestions.length > 0) {
      selectedIndex = selectedIndex >= Math.min(suggestions.length, 8) - 1 ? 0 : selectedIndex + 1;
      renderSuggestions();
    }
    return;
  }

  if (e.key === 'Enter') {
    e.preventDefault();
    e.stopPropagation();
    if (selectedIndex >= 0 && selectedIndex < suggestions.length) {
      acceptSuggestion(selectedIndex);
    } else {
      tryMove();
    }
    return;
  }
}

function tryMove() {
  const san = field.value.trim();
  if (!san) return;

  const game = cfg.getGame();
  const board = cfg.getBoard();
  if (!game || !board) return;

  let move = game.move(san);
  if (!move) {
    move = game.move(san, { sloppy: true });
  }
  if (!move && /^[a-h][18]$/.test(san)) {
    move = game.move(san + '=Q');
    if (!move) move = game.move(san + '=Q', { sloppy: true });
  }

  if (!move) {
    showError(t('trainer.vim.illegal_move'));
    return;
  }

  board.setPosition(game.fen(), game);
  hide();

  if (cfg.onMoveComplete) {
    cfg.onMoveComplete(move);
  }
}
