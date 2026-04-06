import type { EventMap } from '../types/events';

type Handler<T> = (data: T) => void;

export class EventBus {
  private _handlers = new Map<string, Handler<never>[]>();

  on<K extends keyof EventMap & string>(event: K, handler: Handler<EventMap[K]>): () => void {
    if (!this._handlers.has(event)) {
      this._handlers.set(event, []);
    }
    this._handlers.get(event)!.push(handler as Handler<never>);
    return () => this.off(event, handler);
  }

  off<K extends keyof EventMap & string>(event: K, handler?: Handler<EventMap[K]>): void {
    const handlers = this._handlers.get(event);
    if (!handlers) return;
    if (handler) {
      this._handlers.set(event, handlers.filter(h => h !== handler));
    } else {
      this._handlers.delete(event);
    }
  }

  emit<K extends keyof EventMap & string>(event: K, data?: EventMap[K]): void {
    const handlers = this._handlers.get(event);
    if (!handlers) return;
    for (const handler of handlers) {
      try {
        (handler as Handler<EventMap[K]>)(data as EventMap[K]);
      } catch (err) {
        console.error(`EventBus handler error for "${event}":`, err);
      }
    }
  }

  once<K extends keyof EventMap & string>(event: K, handler: Handler<EventMap[K]>): () => void {
    const wrapper = ((data: EventMap[K]) => {
      this.off(event, wrapper as Handler<EventMap[K]>);
      handler(data);
    }) as Handler<EventMap[K]>;
    return this.on(event, wrapper);
  }
}

export const bus = new EventBus();
