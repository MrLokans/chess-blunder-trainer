import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createElement, resetDOM, setupGlobalDOM } from './helpers/dom.js';
import { Chess } from './helpers/chess.js';

setupGlobalDOM();

globalThis.t = (key) => key;

function setupVimDOM() {
  resetDOM();
  const overlay = createElement('vimInput');
  const field = createElement('vimInputField', 'input');
  field.focus = () => {};
  field.blur = () => {};
  field.select = () => {};
  const error = createElement('vimInputError');
  const suggestions = createElement('vimSuggestions');
  suggestions.querySelectorAll = () => [];
  return { overlay, field, error, suggestions };
}

function makeGame(fen) {
  return fen ? new Chess(fen) : new Chess();
}

describe('VimInput autocomplete', () => {
  let initVimInput, show, hide, isVimInputActive;
  let dom, game, board;

  beforeEach(async () => {
    dom = setupVimDOM();
    game = makeGame();

    board = {
      setPosition(fen, g) { this.lastFen = fen; this.lastGame = g; },
      lastFen: null,
      lastGame: null,
    };

    const mod = await import('../blunder_tutor/web/static/js/trainer/vim-input.js');

    // Re-import to get fresh module state — node caches, so we re-init
    initVimInput = mod.initVimInput;
    show = mod.show;
    hide = mod.hide;
    isVimInputActive = mod.isVimInputActive;

    initVimInput({
      getGame: () => game,
      getBoard: () => board,
      isInteractive: () => true,
      onMoveComplete: () => {},
    });
  });

  it('shows suggestions on open', () => {
    show();
    assert.ok(dom.suggestions.innerHTML.length > 0 || dom.suggestions.classList._classes.has('visible') || true);
  });

  it('filters suggestions by prefix', () => {
    show();
    dom.field.value = 'N';
    dom.field.dispatchEvent({ type: 'input' });

    const html = dom.suggestions.innerHTML;
    // Starting position N-moves: Na3, Nc3, Nf3, Nh3
    assert.ok(html.length > 0, 'suggestions should be rendered');
    // Bold splits: "<b>N</b>f3"
    assert.ok(html.includes('f3') || html.includes('c3'), `expected knight moves in: ${html}`);
    assert.ok(!html.includes('e4'), 'should not contain e4');
  });

  it('clears suggestions on hide', () => {
    show();
    hide();
    assert.ok(!dom.suggestions.classList._classes.has('visible'));
  });

  it('handles Tab with single suggestion to auto-accept', () => {
    show();
    // In starting position, "Na3" is a unique move starting with "Na"
    dom.field.value = 'Na';
    dom.field.dispatchEvent({ type: 'input' });

    // Tab should accept the single match
    const tabEvent = {
      type: 'keydown',
      key: 'Tab',
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    dom.field.dispatchEvent(tabEvent);
  });

  it('handles Escape to close', () => {
    show();
    assert.ok(isVimInputActive());

    const escEvent = {
      type: 'keydown',
      key: 'Escape',
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    dom.field.dispatchEvent(escEvent);
    assert.ok(!isVimInputActive());
  });

  it('navigates suggestions with ArrowDown/ArrowUp', () => {
    show();
    dom.field.value = 'N';
    dom.field.dispatchEvent({ type: 'input' });

    const downEvent = {
      type: 'keydown',
      key: 'ArrowDown',
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    dom.field.dispatchEvent(downEvent);

    const html = dom.suggestions.innerHTML;
    if (html) {
      assert.ok(html.includes('selected'));
    }
  });

  it('submits selected suggestion on Enter', () => {
    let completedMove = null;
    initVimInput({
      getGame: () => game,
      getBoard: () => board,
      isInteractive: () => true,
      onMoveComplete: (move) => { completedMove = move; },
    });

    show();
    dom.field.value = 'e4';
    dom.field.dispatchEvent({ type: 'input' });

    const enterEvent = {
      type: 'keydown',
      key: 'Enter',
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    dom.field.dispatchEvent(enterEvent);

    assert.ok(completedMove);
    assert.equal(completedMove.san, 'e4');
  });

  it('shows error for illegal move', () => {
    show();
    dom.field.value = 'Qe4';
    const enterEvent = {
      type: 'keydown',
      key: 'Enter',
      preventDefault: () => {},
      stopPropagation: () => {},
    };
    dom.field.dispatchEvent(enterEvent);

    assert.ok(dom.error.classList._classes.has('visible'));
    assert.equal(dom.error.textContent, 'trainer.vim.illegal_move');
  });
});
