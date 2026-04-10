import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useWebSocket } from '../../src/hooks/useWebSocket';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  sent: string[] = [];
  readyState = 1;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => this.onopen?.(), 0);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  simulateMessage(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) });
  }
}

describe('useWebSocket', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('connects and subscribes to events', async () => {
    renderHook(() => useWebSocket(['stats.updated', 'job.progress']));

    await vi.waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
      const ws = MockWebSocket.instances[0] as MockWebSocket;
      expect(ws.sent.length).toBeGreaterThan(0);
    });

    const ws = MockWebSocket.instances[0] as MockWebSocket;
    const subMessage = ws.sent.find(s => s.includes('subscribe'));
    expect(subMessage).toBeDefined();

    const parsed = JSON.parse(subMessage as string) as { action: string; events: string[] };
    expect(parsed.events).toContain('stats.updated');
    expect(parsed.events).toContain('job.progress');
  });

  test('delivers messages via on() handler', async () => {
    const handler = vi.fn();
    const { result } = renderHook(() => useWebSocket(['stats.updated']));

    await vi.waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    result.current.on('stats.updated', handler);
    const ws = MockWebSocket.instances[0] as MockWebSocket;

    await act(() => {
      ws.simulateMessage({ type: 'stats.updated', data: { total: 42 } });
    });

    expect(handler).toHaveBeenCalledWith({ total: 42 });
  });

  test('disconnects on unmount', async () => {
    const { unmount } = renderHook(() => useWebSocket(['stats.updated']));

    await vi.waitFor(() => {
      expect(MockWebSocket.instances).toHaveLength(1);
    });

    const ws = MockWebSocket.instances[0] as MockWebSocket;
    unmount();
    expect(ws.readyState).toBe(3);
  });
});
