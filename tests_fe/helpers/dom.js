const elements = new Map();

export function createElement(id, tag = 'div') {
  const el = {
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
      add(...cls) { cls.forEach(c => this._classes.add(c)); },
      remove(...cls) { cls.forEach(c => this._classes.delete(c)); },
      contains(c) { return this._classes.has(c); },
      toggle(c) {
        if (this._classes.has(c)) { this._classes.delete(c); return false; }
        this._classes.add(c); return true;
      },
    },
    _listeners: {},
    addEventListener(type, fn) {
      if (!this._listeners[type]) this._listeners[type] = [];
      this._listeners[type].push(fn);
    },
    removeEventListener(type, fn) {
      if (this._listeners[type]) {
        this._listeners[type] = this._listeners[type].filter(h => h !== fn);
      }
    },
    dispatchEvent(evt) {
      const handlers = this._listeners[evt.type] || [];
      handlers.forEach(h => h(evt));
    },
  };
  elements.set(id, el);
  return el;
}

export function resetDOM() {
  elements.clear();
}

export function setupGlobalDOM() {
  globalThis.document = {
    getElementById(id) { return elements.get(id) || null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    documentElement: { style: { setProperty() {} } },
  };

  globalThis.window = globalThis.window || {};
  globalThis.window.location = { protocol: 'http:', host: 'localhost:8000' };

  globalThis.localStorage = {
    _store: {},
    getItem(k) { return this._store[k] ?? null; },
    setItem(k, v) { this._store[k] = String(v); },
    removeItem(k) { delete this._store[k]; },
    clear() { this._store = {}; },
  };
}
