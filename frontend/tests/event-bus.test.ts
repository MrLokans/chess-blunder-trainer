import { describe, it, expect, beforeEach, vi } from 'vitest';
import { EventBus } from '../src/shared/event-bus';

describe('EventBus', () => {
  let bus: EventBus;

  beforeEach(() => {
    bus = new EventBus();
  });

  it('calls handler on emit', () => {
    const calls: unknown[] = [];
    bus.on('puzzle:loaded', (data) => calls.push(data));
    bus.emit('puzzle:loaded', { fen: 'test', moveIndex: 0, gameId: 'g1' });
    expect(calls.length).toBe(1);
    expect(calls[0]).toEqual({ fen: 'test', moveIndex: 0, gameId: 'g1' });
  });

  it('supports multiple handlers for the same event', () => {
    let a = 0, b = 0;
    bus.on('board:reset', () => a++);
    bus.on('board:reset', () => b++);
    bus.emit('board:reset');
    expect(a).toBe(1);
    expect(b).toBe(1);
  });

  it('does not call handlers for other events', () => {
    let called = false;
    bus.on('ws:connected', () => { called = true; });
    bus.emit('board:reset');
    expect(called).toBe(false);
  });

  it('removes specific handler with off', () => {
    let count = 0;
    const handler = () => { count++; };
    bus.on('board:reset', handler);
    bus.emit('board:reset');
    expect(count).toBe(1);

    bus.off('board:reset', handler);
    bus.emit('board:reset');
    expect(count).toBe(1);
  });

  it('removes all handlers for event with off(event)', () => {
    let a = 0, b = 0;
    bus.on('board:reset', () => a++);
    bus.on('board:reset', () => b++);
    bus.off('board:reset');
    bus.emit('board:reset');
    expect(a).toBe(0);
    expect(b).toBe(0);
  });

  it('on returns unsubscribe function', () => {
    let count = 0;
    const unsub = bus.on('board:reset', () => count++);
    bus.emit('board:reset');
    expect(count).toBe(1);

    unsub();
    bus.emit('board:reset');
    expect(count).toBe(1);
  });

  it('once fires handler only once', () => {
    let count = 0;
    bus.once('board:reset', () => count++);
    bus.emit('board:reset');
    bus.emit('board:reset');
    expect(count).toBe(1);
  });

  it('does not throw when emitting events with no handlers', () => {
    expect(() => bus.emit('ws:disconnected')).not.toThrow();
  });

  it('catches handler errors without breaking other handlers', () => {
    let secondCalled = false;
    const errorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    bus.on('board:reset', () => { throw new Error('boom'); });
    bus.on('board:reset', () => { secondCalled = true; });
    bus.emit('board:reset');

    expect(secondCalled).toBe(true);
    expect(errorSpy).toHaveBeenCalledTimes(1);
    errorSpy.mockRestore();
  });
});
