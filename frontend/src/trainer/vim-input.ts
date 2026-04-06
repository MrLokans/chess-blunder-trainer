interface VimInputConfig {
  getGame: () => ChessInstance | null;
  getBoard: () => { setPosition(fen: string, game: ChessInstance): void } | null;
  isInteractive: () => boolean;
  onMoveComplete?: (move: { san: string; from: string; to: string }) => void;
}

let overlay: HTMLElement | null = null;
let field: HTMLInputElement | null = null;
let errorEl: HTMLElement | null = null;
let suggestionsEl: HTMLElement | null = null;
let cfg: VimInputConfig = {
  getGame: () => null,
  getBoard: () => null,
  isInteractive: () => false,
};
let active = false;
let suggestions: string[] = [];
let selectedIndex = -1;

export function initVimInput(config: VimInputConfig): void {
  cfg = config;
  overlay = document.getElementById('vimInput');
  field = document.getElementById('vimInputField') as HTMLInputElement | null;
  errorEl = document.getElementById('vimInputError');
  suggestionsEl = document.getElementById('vimSuggestions');
  if (!overlay || !field) return;

  field.addEventListener('keydown', onKeyDown);
  field.addEventListener('input', onInput);
  overlay.addEventListener('animationend', () => overlay!.classList.remove('shake'));
}

export function show(): void {
  if (!overlay || !field || !cfg.isInteractive()) return;
  active = true;
  field.value = '';
  if (errorEl) {
    errorEl.classList.remove('visible');
    errorEl.textContent = '';
  }
  clearSuggestions();
  overlay.classList.add('active');
  field.focus();
  updateSuggestions();
}

export function hide(): void {
  if (!overlay || !field) return;
  active = false;
  clearSuggestions();
  overlay.classList.remove('active');
  field.blur();
}

export function isVimInputActive(): boolean {
  return active;
}

function showError(msg: string): void {
  if (!errorEl || !overlay || !field) return;
  errorEl.textContent = msg;
  errorEl.classList.add('visible');
  overlay.classList.add('shake');
  field.select();
  setTimeout(() => errorEl!.classList.remove('visible'), 1500);
}

function getLegalMoves(): string[] {
  const game = cfg.getGame();
  if (!game) return [];
  return game.moves() as string[];
}

function updateSuggestions(): void {
  if (!field) return;
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

function renderSuggestions(): void {
  if (!suggestionsEl || !field) return;

  if (suggestions.length === 0 || (suggestions.length === 1 && suggestions[0] === field.value.trim())) {
    suggestionsEl.classList.remove('visible');
    suggestionsEl.innerHTML = '';
    return;
  }

  const maxVisible = 8;
  const visible = suggestions.slice(0, maxVisible);

  suggestionsEl.innerHTML = visible.map((move, i) => {
    const cls = i === selectedIndex ? 'vim-suggestion selected' : 'vim-suggestion';
    const input = field!.value.trim();
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
      const idx = parseInt((el as HTMLElement).dataset['index'] ?? '0', 10);
      acceptSuggestion(idx);
    });
  });
}

function acceptSuggestion(index: number): void {
  if (index >= 0 && index < suggestions.length && field) {
    field.value = suggestions[index]!;
    clearSuggestions();
    tryMove();
  }
}

function clearSuggestions(): void {
  suggestions = [];
  selectedIndex = -1;
  if (suggestionsEl) {
    suggestionsEl.classList.remove('visible');
    suggestionsEl.innerHTML = '';
  }
}

function onInput(): void {
  updateSuggestions();
}

function onKeyDown(e: KeyboardEvent): void {
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

function tryMove(): void {
  if (!field) return;
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
    if (!move) move = game.move(san + '=Q', { sloppy: true } as never);
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
