import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';
import { setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

let wsInstances = [];

class MockWebSocket {
  constructor(url) {
    this.url = url;
    this.sent = [];
    this.readyState = 1;
    wsInstances.push(this);
    setTimeout(() => this.onopen?.(), 0);
  }
  send(data) { this.sent.push(JSON.parse(data)); }
  close() { this.onclose?.(); }
}

globalThis.WebSocket = MockWebSocket;

const { WebSocketClient } = await import('../blunder_tutor/web/static/js/websocket-client.js');

describe('WebSocketClient', () => {
  beforeEach(() => {
    wsInstances = [];
  });

  it('builds correct WS URL', () => {
    const client = new WebSocketClient('/ws');
    assert.equal(client.url, 'ws://localhost:8000/ws');
  });

  it('registers and dispatches event handlers', () => {
    const client = new WebSocketClient();
    const received = [];
    client.on('job.progress', (data) => received.push(data));
    client.handleMessage({ type: 'job.progress', data: { percent: 50 } });
    assert.deepEqual(received, [{ percent: 50 }]);
  });

  it('supports multiple handlers per event', () => {
    const client = new WebSocketClient();
    const a = [], b = [];
    client.on('test', (d) => a.push(d));
    client.on('test', (d) => b.push(d));
    client.handleMessage({ type: 'test', data: 'x' });
    assert.deepEqual(a, ['x']);
    assert.deepEqual(b, ['x']);
  });

  it('unsubscribes specific handler with off()', () => {
    const client = new WebSocketClient();
    const received = [];
    const handler = (d) => received.push(d);
    client.on('test', handler);
    client.off('test', handler);
    client.handleMessage({ type: 'test', data: 'x' });
    assert.deepEqual(received, []);
  });

  it('unsubscribes all handlers for event with off()', () => {
    const client = new WebSocketClient();
    const received = [];
    client.on('test', (d) => received.push(d));
    client.on('test', (d) => received.push(d));
    client.off('test');
    client.handleMessage({ type: 'test', data: 'x' });
    assert.deepEqual(received, []);
  });

  it('deduplicates subscription event types', () => {
    const client = new WebSocketClient();
    client.subscribe(['a', 'b']);
    client.subscribe(['b', 'c']);
    assert.deepEqual(client.subscriptions, ['a', 'b', 'c']);
  });

  it('ignores handler errors without crashing', () => {
    const client = new WebSocketClient();
    client.on('test', () => { throw new Error('boom'); });
    const received = [];
    client.on('test', (d) => received.push(d));
    client.handleMessage({ type: 'test', data: 'ok' });
    assert.deepEqual(received, ['ok']);
  });

  it('handles messages with no registered handlers', () => {
    const client = new WebSocketClient();
    assert.doesNotThrow(() => {
      client.handleMessage({ type: 'unknown', data: {} });
    });
  });
});
