class EventBus {
  constructor() {
    this._handlers = new Map();
  }

  on(event, handler) {
    if (!this._handlers.has(event)) {
      this._handlers.set(event, []);
    }
    this._handlers.get(event).push(handler);
    return () => this.off(event, handler);
  }

  off(event, handler) {
    const handlers = this._handlers.get(event);
    if (!handlers) return;
    if (handler) {
      this._handlers.set(event, handlers.filter(h => h !== handler));
    } else {
      this._handlers.delete(event);
    }
  }

  emit(event, data) {
    const handlers = this._handlers.get(event);
    if (!handlers) return;
    for (const handler of handlers) {
      try {
        handler(data);
      } catch (err) {
        console.error(`EventBus handler error for "${event}":`, err);
      }
    }
  }

  once(event, handler) {
    const wrapper = (data) => {
      this.off(event, wrapper);
      handler(data);
    };
    return this.on(event, wrapper);
  }
}

export const bus = new EventBus();
export { EventBus };
