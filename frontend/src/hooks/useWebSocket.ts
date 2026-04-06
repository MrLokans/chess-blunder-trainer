import { useEffect, useRef, useCallback } from 'preact/hooks';

interface WsMessage {
  type: string;
  data: unknown;
}

type WsHandler = (data: unknown) => void;

export interface UseWebSocketResult {
  on: (eventType: string, handler: WsHandler) => () => void;
}

export function useWebSocket(events: string[]): UseWebSocketResult {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(new Map<string, WsHandler[]>());
  const eventsKey = events.join(',');

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ action: 'subscribe', events }));
    };

    ws.onmessage = (event: MessageEvent) => {
      const message = JSON.parse(event.data as string) as WsMessage;
      const handlers = handlersRef.current.get(message.type) ?? [];
      for (const handler of handlers) {
        try {
          handler(message.data);
        } catch (err) {
          console.error(`WebSocket handler error for "${message.type}":`, err);
        }
      }
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [eventsKey]);

  const on = useCallback((eventType: string, handler: WsHandler): (() => void) => {
    const handlers = handlersRef.current;
    const existing = handlers.get(eventType);
    if (existing) {
      existing.push(handler);
    } else {
      handlers.set(eventType, [handler]);
    }

    return () => {
      const list = handlers.get(eventType);
      if (list) {
        handlers.set(eventType, list.filter(h => h !== handler));
      }
    };
  }, []);

  return { on };
}
