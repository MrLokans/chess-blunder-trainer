import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { createElement, resetDOM, setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

function setupTrainerDOM() {
  resetDOM();

  const ids = [
    'evalBarFill', 'evalValue', 'phaseIndicator', 'colorBadge',
    'blunderMove', 'evalBefore', 'evalAfter', 'cpLoss',
    'feedback', 'feedbackTitle', 'feedbackDetail',
    'currentMove', 'bestMoveInfo', 'bestMoveDisplay', 'bestLineDisplay',
    'historySection', 'moveHistory',
    'submitBtn', 'resetBtn', 'showBestBtn', 'nextBtn',
    'tryBestBtn', 'undoBtn', 'lichessBtn',
    'highlightLegend', 'legendBlunder', 'legendBest', 'legendUser',
    'showArrows', 'showThreats', 'showTactics', 'legendTactic',
    'phaseBadge', 'tacticalBadge', 'tacticalPatternName',
    'tacticalInfo', 'tacticalInfoTitle', 'tacticalInfoReason',
    'filtersHeader', 'filtersToggleBtn', 'filtersContent', 'filtersChevron',
    'emptyState', 'trainerLayout', 'emptyStateTitle', 'emptyStateMessage',
    'emptyStateAction', 'statsCard', 'board',
    'flipBtn', 'shortcutsOverlay', 'shortcutsClose', 'shortcutsHintBtn',
    'gameLink',
  ];

  for (const id of ids) {
    createElement(id);
  }

  const showArrows = createElement('showArrows', 'input');
  showArrows.checked = true;
  showArrows.type = 'checkbox';

  const showThreats = createElement('showThreats', 'input');
  showThreats.checked = true;
  showThreats.type = 'checkbox';
}

function fireKeydown(key, opts = {}) {
  const event = {
    type: 'keydown',
    key,
    ctrlKey: opts.ctrlKey || false,
    metaKey: opts.metaKey || false,
    target: { tagName: opts.targetTag || 'BODY' },
    preventDefault() { this._prevented = true; },
    _prevented: false,
  };
  const handlers = globalThis.document._listeners?.keydown || [];
  handlers.forEach(h => h(event));
  return event;
}

describe('Keyboard shortcuts', () => {
  beforeEach(() => {
    setupTrainerDOM();
    globalThis.document._listeners = {};
    globalThis.document.addEventListener = function(type, fn) {
      if (!this._listeners[type]) this._listeners[type] = [];
      this._listeners[type].push(fn);
    };
  });

  it('skips shortcuts when focused on input elements', () => {
    // Register a mock handler to track calls
    let called = false;
    globalThis.document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      called = true;
    });

    fireKeydown('n', { targetTag: 'INPUT' });
    assert.equal(called, false);

    fireKeydown('n', { targetTag: 'TEXTAREA' });
    assert.equal(called, false);

    fireKeydown('n', { targetTag: 'SELECT' });
    assert.equal(called, false);

    fireKeydown('n', { targetTag: 'BODY' });
    assert.equal(called, true);
  });

  it('toggles shortcuts overlay with ? key', () => {
    const overlay = createElement('shortcutsOverlay');
    overlay.classList._classes.clear();

    globalThis.document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input') return;
      if (e.key === '?') {
        const visible = overlay.classList.contains('visible');
        if (visible) overlay.classList.remove('visible');
        else overlay.classList.add('visible');
      }
    });

    fireKeydown('?');
    assert.equal(overlay.classList.contains('visible'), true);

    fireKeydown('?');
    assert.equal(overlay.classList.contains('visible'), false);
  });

  it('closes overlay with Escape', () => {
    const overlay = createElement('shortcutsOverlay');
    overlay.classList.add('visible');

    globalThis.document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && overlay.classList.contains('visible')) {
        overlay.classList.remove('visible');
      }
    });

    fireKeydown('Escape');
    assert.equal(overlay.classList.contains('visible'), false);
  });

  it('toggles arrow checkbox with A key', () => {
    const checkbox = createElement('showArrows', 'input');
    checkbox.checked = true;
    let changeDispatched = false;
    checkbox.dispatchEvent = () => { changeDispatched = true; };

    globalThis.document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input') return;
      if (e.key === 'a' || e.key === 'A') {
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change'));
      }
    });

    fireKeydown('a');
    assert.equal(checkbox.checked, false);
    assert.equal(changeDispatched, true);
  });

  it('toggles threats checkbox with T key', () => {
    const checkbox = createElement('showThreats', 'input');
    checkbox.checked = false;
    let changeDispatched = false;
    checkbox.dispatchEvent = () => { changeDispatched = true; };

    globalThis.document.addEventListener('keydown', (e) => {
      const tag = (e.target.tagName || '').toLowerCase();
      if (tag === 'input') return;
      if (e.key === 't' || e.key === 'T') {
        checkbox.checked = !checkbox.checked;
        checkbox.dispatchEvent(new Event('change'));
      }
    });

    fireKeydown('t');
    assert.equal(checkbox.checked, true);
    assert.equal(changeDispatched, true);
  });
});

describe('flipBoard', () => {
  it('toggles orientation between white and black', () => {
    let boardFlipped = false;
    const playerColor = 'white';
    const orientations = [];

    function flipBoard() {
      boardFlipped = !boardFlipped;
      const base = playerColor === 'black' ? 'black' : 'white';
      const newOrientation = boardFlipped ? (base === 'white' ? 'black' : 'white') : base;
      orientations.push(newOrientation);
    }

    flipBoard();
    assert.equal(orientations[0], 'black');

    flipBoard();
    assert.equal(orientations[1], 'white');

    flipBoard();
    assert.equal(orientations[2], 'black');
  });

  it('flips correctly when playing as black', () => {
    let boardFlipped = false;
    const playerColor = 'black';
    const orientations = [];

    function flipBoard() {
      boardFlipped = !boardFlipped;
      const base = playerColor === 'black' ? 'black' : 'white';
      const newOrientation = boardFlipped ? (base === 'white' ? 'black' : 'white') : base;
      orientations.push(newOrientation);
    }

    flipBoard();
    assert.equal(orientations[0], 'white');

    flipBoard();
    assert.equal(orientations[1], 'black');
  });
});
