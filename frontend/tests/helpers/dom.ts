interface MockElement {
  id: string;
  tagName: string;
  textContent: string;
  innerHTML: string;
  className: string;
  value: string;
  checked: boolean;
  style: Record<string, string>;
  classList: {
    _classes: Set<string>;
    add(...cls: string[]): void;
    remove(...cls: string[]): void;
    contains(c: string): boolean;
    toggle(c: string): boolean;
  };
  _listeners: Record<string, Array<(evt: unknown) => void>>;
  addEventListener(type: string, fn: (evt: unknown) => void): void;
  removeEventListener(type: string, fn: (evt: unknown) => void): void;
  dispatchEvent(evt: { type: string }): void;
}

const elements = new Map<string, MockElement>();

export function createElement(id: string, tag = 'div'): MockElement {
  const el: MockElement = {
    id,
    tagName: tag.toUpperCase(),
    textContent: '',
    innerHTML: '',
    className: '',
    value: '',
    checked: false,
    style: { display: '', width: '' },
    classList: {
      _classes: new Set(),
      add(...cls: string[]) { cls.forEach(c => this._classes.add(c)); },
      remove(...cls: string[]) { cls.forEach(c => this._classes.delete(c)); },
      contains(c: string) { return this._classes.has(c); },
      toggle(c: string) {
        if (this._classes.has(c)) { this._classes.delete(c); return false; }
        this._classes.add(c); return true;
      },
    },
    _listeners: {},
    addEventListener(type: string, fn: (evt: unknown) => void) {
      if (!this._listeners[type]) this._listeners[type] = [];
      this._listeners[type].push(fn);
    },
    removeEventListener(type: string, fn: (evt: unknown) => void) {
      if (this._listeners[type]) {
        this._listeners[type] = this._listeners[type].filter(h => h !== fn);
      }
    },
    dispatchEvent(evt: { type: string }) {
      const handlers = this._listeners[evt.type] ?? [];
      handlers.forEach(h => h(evt));
    },
  };
  elements.set(id, el);
  return el;
}

export function resetDOM(): void {
  elements.clear();
}

export function getElement(id: string): MockElement | undefined {
  return elements.get(id);
}
