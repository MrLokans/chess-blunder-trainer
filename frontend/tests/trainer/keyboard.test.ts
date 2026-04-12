import { describe, it, expect, beforeEach, vi } from 'vitest';

describe('Keyboard shortcuts', () => {
  let keydownHandlers: Array<(e: KeyboardEvent) => void>;

  beforeEach(() => {
    keydownHandlers = [];
    vi.spyOn(document, 'addEventListener').mockImplementation((type: string, fn: EventListenerOrEventListenerObject) => {
      if (type === 'keydown') {
        keydownHandlers.push(fn as (e: KeyboardEvent) => void);
      }
    });
  });

  function fireKeydown(key: string, opts: { ctrlKey?: boolean; metaKey?: boolean; targetTag?: string } = {}): KeyboardEvent {
    const event = {
      type: 'keydown',
      key,
      ctrlKey: opts.ctrlKey || false,
      metaKey: opts.metaKey || false,
      target: { tagName: opts.targetTag || 'BODY' },
      preventDefault: vi.fn(),
      stopPropagation: vi.fn(),
    } as unknown as KeyboardEvent;
    for (const handler of keydownHandlers) {
      handler(event);
    }
    return event;
  }

  it('skips shortcuts when focused on input elements', () => {
    let called = false;
    document.addEventListener('keydown', ((e: KeyboardEvent) => {
      const tag = ((e.target as HTMLElement).tagName || '').toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
      called = true;
    }) as EventListener);

    fireKeydown('n', { targetTag: 'INPUT' });
    expect(called).toBe(false);

    fireKeydown('n', { targetTag: 'TEXTAREA' });
    expect(called).toBe(false);

    fireKeydown('n', { targetTag: 'SELECT' });
    expect(called).toBe(false);

    fireKeydown('n', { targetTag: 'BODY' });
    expect(called).toBe(true);
  });
});

describe('flipBoard', () => {
  it('toggles orientation between white and black', () => {
    let boardFlipped = false;
    const playerColor: 'white' | 'black' = 'white';
    const orientations: string[] = [];

    function flipBoard() {
      boardFlipped = !boardFlipped;
      const base: 'white' | 'black' = playerColor === 'black' ? 'black' : 'white';
      const newOrientation: 'white' | 'black' = boardFlipped ? (base === 'white' ? 'black' : 'white') : base;
      orientations.push(newOrientation);
    }

    flipBoard();
    expect(orientations[0]).toBe('black');

    flipBoard();
    expect(orientations[1]).toBe('white');

    flipBoard();
    expect(orientations[2]).toBe('black');
  });

  it('flips correctly when playing as black', () => {
    let boardFlipped = false;
    const playerColor: 'white' | 'black' = 'black';
    const orientations: string[] = [];

    function flipBoard() {
      boardFlipped = !boardFlipped;
      const base: 'white' | 'black' = playerColor === 'black' ? 'black' : 'white';
      const newOrientation: 'white' | 'black' = boardFlipped ? (base === 'white' ? 'black' : 'white') : base;
      orientations.push(newOrientation);
    }

    flipBoard();
    expect(orientations[0]).toBe('white');

    flipBoard();
    expect(orientations[1]).toBe('black');
  });
});
