import { describe, it, expect, beforeEach, vi } from 'vitest';
import { loadChessGlobal } from '../helpers/chess';
import { createElement, resetDOM } from '../helpers/dom';

loadChessGlobal();

function setupVimDOM() {
  resetDOM();
  const overlay = createElement('vimInput');
  const field = createElement('vimInputField', 'input') as unknown as HTMLInputElement & {
    _listeners: Record<string, Array<(evt: unknown) => void>>;
    focus: () => void;
    blur: () => void;
    select: () => void;
  };
  field.focus = vi.fn();
  field.blur = vi.fn();
  field.select = vi.fn();
  const error = createElement('vimInputError');
  const suggestions = createElement('vimSuggestions');
  (suggestions as unknown as { querySelectorAll: () => never[] }).querySelectorAll = () => [];
  return { overlay, field, error, suggestions };
}

describe('VimInput autocomplete', () => {
  let dom: ReturnType<typeof setupVimDOM>;
  let game: ChessInstance;
  let board: { setPosition: (fen: string, g: ChessInstance) => void; lastFen: string | null; lastGame: ChessInstance | null };

  beforeEach(async () => {
    dom = setupVimDOM();

    vi.spyOn(document, 'getElementById').mockImplementation((id: string) => {
      if (id === 'vimInput') return dom.overlay as unknown as HTMLElement;
      if (id === 'vimInputField') return dom.field as unknown as HTMLElement;
      if (id === 'vimInputError') return dom.error as unknown as HTMLElement;
      if (id === 'vimSuggestions') return dom.suggestions as unknown as HTMLElement;
      return null;
    });

    game = new Chess();
    board = {
      setPosition(fen: string, g: ChessInstance) { this.lastFen = fen; this.lastGame = g; },
      lastFen: null,
      lastGame: null,
    };

    const mod = await import('../../src/trainer/vim-input');

    mod.initVimInput({
      getGame: () => game,
      getBoard: () => board as never,
      isInteractive: () => true,
      onMoveComplete: vi.fn(),
    });
  });

  it('shows overlay on open', async () => {
    const mod = await import('../../src/trainer/vim-input');
    mod.show();
    expect(mod.isVimInputActive()).toBe(true);
  });

  it('hides overlay on hide', async () => {
    const mod = await import('../../src/trainer/vim-input');
    mod.show();
    mod.hide();
    expect(mod.isVimInputActive()).toBe(false);
  });

  it('handles Escape to close', async () => {
    const mod = await import('../../src/trainer/vim-input');
    mod.show();
    expect(mod.isVimInputActive()).toBe(true);

    dom.field.dispatchEvent({
      type: 'keydown',
      key: 'Escape',
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
    } as unknown as Event);

    expect(mod.isVimInputActive()).toBe(false);
  });

  it('submits a valid move on Enter', async () => {
    const completedMove = vi.fn();

    const mod = await import('../../src/trainer/vim-input');
    mod.initVimInput({
      getGame: () => game,
      getBoard: () => board as never,
      isInteractive: () => true,
      onMoveComplete: completedMove,
    });

    mod.show();
    dom.field.value = 'e4';
    dom.field.dispatchEvent({ type: 'input' } as Event);

    dom.field.dispatchEvent({
      type: 'keydown',
      key: 'Enter',
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
    } as unknown as Event);

    expect(completedMove).toHaveBeenCalled();
    const call = completedMove.mock.calls[0]![0] as { san: string };
    expect(call.san).toBe('e4');
  });

  it('shows error for illegal move', async () => {
    const mod = await import('../../src/trainer/vim-input');
    mod.show();
    dom.field.value = 'Qe4';

    dom.field.dispatchEvent({
      type: 'keydown',
      key: 'Enter',
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
    } as unknown as Event);

    expect(dom.error.classList.contains('visible')).toBe(true);
    expect(dom.error.textContent).toBe('trainer.vim.illegal_move');
  });
});
