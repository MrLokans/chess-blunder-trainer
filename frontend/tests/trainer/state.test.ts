import { describe, it, expect, beforeEach, vi } from 'vitest';
import { EventBus } from '../../src/shared/event-bus';

vi.mock('../../src/shared/event-bus', () => {
  const EventBusClass = vi.fn();
  const instance = {
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn(),
    once: vi.fn(),
  };
  EventBusClass.prototype = instance;
  return {
    EventBus: EventBusClass,
    bus: instance,
  };
});

import * as state from '../../src/trainer/state';
import { bus } from '../../src/shared/event-bus';

describe('trainer state', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    state.resetForNewPuzzle();
  });

  it('resetForNewPuzzle clears transient state', () => {
    state.set('submitted', true);
    state.set('bestRevealed', true);
    state.set('boardFlipped', true);
    state.set('moveHistory', ['e4', 'e5']);
    state.set('linePositions', [{ fen: 'abc', moveHistory: [] }]);
    state.set('lineViewIndex', 2);
    state.set('animatingLine', true);
    state.set('currentStarred', true);

    state.resetForNewPuzzle();

    expect(state.get('submitted')).toBe(false);
    expect(state.get('bestRevealed')).toBe(false);
    expect(state.get('boardFlipped')).toBe(false);
    expect(state.get('moveHistory')).toEqual([]);
    expect(state.get('linePositions')).toEqual([]);
    expect(state.get('lineViewIndex')).toBe(-1);
    expect(state.get('animatingLine')).toBe(false);
    expect(state.get('currentStarred')).toBe(false);
  });

  it('preserves board and game references across reset', () => {
    const mockBoard = { id: 'board1' } as unknown as ReturnType<typeof state.get<'board'>>;
    const mockGame = { id: 'game1' } as unknown as ReturnType<typeof state.get<'game'>>;
    state.set('board', mockBoard);
    state.set('game', mockGame);

    state.resetForNewPuzzle();

    expect(state.get('board')).toBe(mockBoard);
    expect(state.get('game')).toBe(mockGame);
  });

  it('pushMove appends to history', () => {
    state.pushMove('e4');
    state.pushMove('e5');
    expect(state.get('moveHistory')).toEqual(['e4', 'e5']);
  });

  it('popMove removes last entry', () => {
    state.pushMove('e4');
    state.pushMove('e5');
    state.pushMove('Nf3');
    const popped = state.popMove();
    expect(popped).toBe('Nf3');
    expect(state.get('moveHistory')).toEqual(['e4', 'e5']);
  });

  it('animationGeneration increments', () => {
    const g1 = state.nextAnimationGeneration();
    const g2 = state.nextAnimationGeneration();
    expect(g2).toBe(g1 + 1);
  });

  it('emits state:changed on set', () => {
    state.set('submitted', true);
    expect(bus.emit).toHaveBeenCalledWith(
      'state:changed',
      expect.objectContaining({ key: 'submitted', value: true }),
    );
  });

  it('emits specific key events on set', () => {
    state.set('bestRevealed', true);
    expect(bus.emit).toHaveBeenCalledWith(
      'state:bestRevealed',
      expect.objectContaining({ value: true }),
    );
  });

  it('isAnimating returns true when animatingLine', () => {
    state.set('animatingLine', true);
    expect(state.isAnimating()).toBe(true);
  });

  it('isAnimating returns true when animatingPreMove', () => {
    state.set('animatingPreMove', true);
    expect(state.isAnimating()).toBe(true);
  });

  it('snapshot returns a shallow copy', () => {
    state.pushMove('e4');
    const snap = state.snapshot();
    state.pushMove('d4');
    expect(snap.moveHistory).toEqual(['e4']);
    expect(state.get('moveHistory')).toEqual(['e4', 'd4']);
  });
});
