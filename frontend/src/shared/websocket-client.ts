export interface WsMessage {
  type: string;
  data: unknown;
}

type WsHandler = (data: unknown, message: WsMessage) => void;

export class WebSocketClient {
  readonly url: string;
  private ws: WebSocket | null = null;
  private reconnectInterval = 3000;
  private handlers: Map<string, WsHandler[]> = new Map();
  subscriptions: string[] = [];
  private connected = false;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private heartbeatInterval: ReturnType<typeof setInterval> | null = null;

  constructor(url = '/ws') {
    this.url = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${url}`;
  }

  connect(): void {
    if (this.ws && this.connected) {
      console.log('WebSocket already connected');
      return;
    }

    console.log('Connecting to WebSocket:', this.url);
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('WebSocket connected');
      this.connected = true;
      this.reconnectAttempts = 0;

      if (this.subscriptions.length > 0) {
        this.subscribe(this.subscriptions);
      }

      this.startHeartbeat();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      const message = JSON.parse(event.data as string) as WsMessage;
      this.handleMessage(message);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
      this.connected = false;

      if (this.heartbeatInterval) {
        clearInterval(this.heartbeatInterval);
      }

      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++;
        const delay = Math.min(30000, this.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1));
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
        setTimeout(() => this.connect(), delay);
      } else {
        console.error('Max reconnection attempts reached');
      }
    };

    this.ws.onerror = (error: Event) => {
      console.error('WebSocket error:', error);
    };
  }

  subscribe(eventTypes: string | string[]): void {
    const types = Array.isArray(eventTypes) ? eventTypes : [eventTypes];
    this.subscriptions = [...new Set([...this.subscriptions, ...types])];

    if (this.connected && this.ws) {
      this.ws.send(JSON.stringify({
        action: 'subscribe',
        events: types,
      }));
    }
  }

  on(eventType: string, handler: WsHandler): void {
    const existing = this.handlers.get(eventType);
    if (existing) {
      existing.push(handler);
    } else {
      this.handlers.set(eventType, [handler]);
    }
  }

  off(eventType: string, handler?: WsHandler): void {
    if (!this.handlers.has(eventType)) return;
    if (handler) {
      const filtered = this.handlers.get(eventType)!.filter(h => h !== handler);
      this.handlers.set(eventType, filtered);
    } else {
      this.handlers.delete(eventType);
    }
  }

  handleMessage(message: WsMessage): void {
    const handlers = this.handlers.get(message.type) ?? [];
    handlers.forEach(handler => {
      try {
        handler(message.data, message);
      } catch (error) {
        console.error('Error in message handler:', error);
      }
    });
  }

  startHeartbeat(): void {
    this.heartbeatInterval = setInterval(() => {
      if (this.connected && this.ws) {
        this.ws.send(JSON.stringify({ action: 'ping' }));
      }
    }, 30000);
  }

  disconnect(): void {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
    }
    if (this.ws) {
      this.reconnectAttempts = this.maxReconnectAttempts;
      this.ws.close();
    }
  }
}
