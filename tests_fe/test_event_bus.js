import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { EventBus } from '../blunder_tutor/web/static/js/event-bus.js';

describe('EventBus', () => {
  let bus;

  beforeEach(() => {
    bus = new EventBus();
  });

  it('calls handler on emit', () => {
    const calls = [];
    bus.on('test', (data) => calls.push(data));
    bus.emit('test', { value: 1 });
    assert.equal(calls.length, 1);
    assert.deepEqual(calls[0], { value: 1 });
  });

  it('supports multiple handlers for the same event', () => {
    let a = 0, b = 0;
    bus.on('test', () => a++);
    bus.on('test', () => b++);
    bus.emit('test');
    assert.equal(a, 1);
    assert.equal(b, 1);
  });

  it('does not call handlers for other events', () => {
    let called = false;
    bus.on('other', () => { called = true; });
    bus.emit('test');
    assert.equal(called, false);
  });

  it('removes specific handler with off', () => {
    let count = 0;
    const handler = () => count++;
    bus.on('test', handler);
    bus.emit('test');
    assert.equal(count, 1);

    bus.off('test', handler);
    bus.emit('test');
    assert.equal(count, 1);
  });

  it('removes all handlers for event with off(event)', () => {
    let a = 0, b = 0;
    bus.on('test', () => a++);
    bus.on('test', () => b++);
    bus.off('test');
    bus.emit('test');
    assert.equal(a, 0);
    assert.equal(b, 0);
  });

  it('on returns unsubscribe function', () => {
    let count = 0;
    const unsub = bus.on('test', () => count++);
    bus.emit('test');
    assert.equal(count, 1);

    unsub();
    bus.emit('test');
    assert.equal(count, 1);
  });

  it('once fires handler only once', () => {
    let count = 0;
    bus.once('test', () => count++);
    bus.emit('test');
    bus.emit('test');
    assert.equal(count, 1);
  });

  it('does not throw when emitting events with no handlers', () => {
    assert.doesNotThrow(() => bus.emit('nonexistent', {}));
  });

  it('catches handler errors without breaking other handlers', () => {
    let secondCalled = false;
    const originalError = console.error;
    const errors = [];
    console.error = (...args) => errors.push(args);

    bus.on('test', () => { throw new Error('boom'); });
    bus.on('test', () => { secondCalled = true; });
    bus.emit('test');

    assert.equal(secondCalled, true);
    assert.equal(errors.length, 1);
    console.error = originalError;
  });
});
