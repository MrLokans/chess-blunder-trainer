import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WebSocketClient } from '../src/shared/websocket-client';

class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((evt: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((err: unknown) => void) | null = null;
  sent: string[] = [];
  send(data: string) { this.sent.push(data); }
  close() { this.onclose?.(); }
}

describe('WebSocketClient', () => {
  let mockWs: MockWebSocket;

  beforeEach(() => {
    vi.restoreAllMocks();
    mockWs = new MockWebSocket();
    vi.stubGlobal('WebSocket', vi.fn(() => mockWs));
  });

  it('builds correct WS URL', () => {
    const wsClient = new WebSocketClient('/ws');
    expect(wsClient.url).toContain('/ws');
    expect(wsClient.url).toMatch(/^wss?:\/\//);
  });

  it('connects to WebSocket URL', () => {
    const wsClient = new WebSocketClient('/ws');
    wsClient.connect();
    expect(WebSocket).toHaveBeenCalledWith(expect.stringContaining('/ws'));
  });

  it('registers and dispatches event handlers', () => {
    const wsClient = new WebSocketClient('/ws');
    const received: unknown[] = [];
    wsClient.on('job.progress', (data) => received.push(data));
    wsClient.handleMessage({ type: 'job.progress', data: { percent: 50 } });
    expect(received).toEqual([{ percent: 50 }]);
  });

  it('supports multiple handlers per event', () => {
    const wsClient = new WebSocketClient('/ws');
    const a: unknown[] = [];
    const b: unknown[] = [];
    wsClient.on('test', (d) => a.push(d));
    wsClient.on('test', (d) => b.push(d));
    wsClient.handleMessage({ type: 'test', data: 'x' });
    expect(a).toEqual(['x']);
    expect(b).toEqual(['x']);
  });

  it('unsubscribes specific handler with off()', () => {
    const wsClient = new WebSocketClient('/ws');
    const received: unknown[] = [];
    const handler = (d: unknown) => received.push(d);
    wsClient.on('test', handler);
    wsClient.off('test', handler);
    wsClient.handleMessage({ type: 'test', data: 'x' });
    expect(received).toEqual([]);
  });

  it('unsubscribes all handlers for event with off()', () => {
    const wsClient = new WebSocketClient('/ws');
    const received: unknown[] = [];
    wsClient.on('test', (d) => received.push(d));
    wsClient.on('test', (d) => received.push(d));
    wsClient.off('test');
    wsClient.handleMessage({ type: 'test', data: 'x' });
    expect(received).toEqual([]);
  });

  it('deduplicates subscription event types', () => {
    const wsClient = new WebSocketClient('/ws');
    wsClient.subscribe(['a', 'b']);
    wsClient.subscribe(['b', 'c']);
    expect(wsClient.subscriptions).toEqual(['a', 'b', 'c']);
  });

  it('subscribes to events after connection', () => {
    const wsClient = new WebSocketClient('/ws');
    wsClient.connect();
    wsClient.subscribe(['job.completed']);
    mockWs.onopen?.();
    const sent = JSON.parse(mockWs.sent[0]!) as { action: string; events: string[] };
    expect(sent.action).toBe('subscribe');
    expect(sent.events).toContain('job.completed');
  });

  it('dispatches messages to handlers', () => {
    const wsClient = new WebSocketClient('/ws');
    const handler = vi.fn();
    wsClient.connect();
    mockWs.onopen?.();
    wsClient.on('job.completed', handler);
    mockWs.onmessage?.({ data: JSON.stringify({ type: 'job.completed', data: { id: 1 } }) });
    expect(handler).toHaveBeenCalledWith({ id: 1 }, expect.objectContaining({ type: 'job.completed' }));
  });

  it('ignores handler errors without crashing', () => {
    const wsClient = new WebSocketClient('/ws');
    wsClient.on('test', () => { throw new Error('boom'); });
    const received: unknown[] = [];
    wsClient.on('test', (d) => received.push(d));
    wsClient.handleMessage({ type: 'test', data: 'ok' });
    expect(received).toEqual(['ok']);
  });

  it('handles messages with no registered handlers', () => {
    const wsClient = new WebSocketClient('/ws');
    expect(() => {
      wsClient.handleMessage({ type: 'unknown', data: {} });
    }).not.toThrow();
  });
});
