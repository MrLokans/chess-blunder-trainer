import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

// i18n.js sets window.t, so we need to provide the globals it reads from
globalThis.window = globalThis.window || {};
globalThis.window.__i18n__ = {};
globalThis.window.__locale__ = 'en';
globalThis.Intl = globalThis.Intl || {};

// Load the module (it attaches window.t on import)
await import('../blunder_tutor/web/static/js/i18n.js');

const t = globalThis.window.t;

describe('t() basic lookup', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'en';
  });

  it('returns the key when not found in dictionary', () => {
    globalThis.window.__i18n__ = {};
    assert.equal(t('missing.key'), 'missing.key');
  });

  it('returns the message for a known key', () => {
    globalThis.window.__i18n__ = { 'hello': 'Hello World' };
    assert.equal(t('hello'), 'Hello World');
  });

  it('returns the raw message when no params provided', () => {
    globalThis.window.__i18n__ = { 'greeting': 'Hi {name}' };
    assert.equal(t('greeting'), 'Hi {name}');
  });
});

describe('t() placeholder substitution', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'en';
  });

  it('replaces a single placeholder', () => {
    globalThis.window.__i18n__ = { 'greet': 'Hello {name}!' };
    assert.equal(t('greet', { name: 'Alice' }), 'Hello Alice!');
  });

  it('replaces multiple placeholders', () => {
    globalThis.window.__i18n__ = { 'info': '{count} games by {user}' };
    assert.equal(t('info', { count: 5, user: 'Bob' }), '5 games by Bob');
  });

  it('leaves unmatched placeholders intact', () => {
    globalThis.window.__i18n__ = { 'partial': '{known} and {unknown}' };
    assert.equal(t('partial', { known: 'yes' }), 'yes and {unknown}');
  });

  it('converts non-string params to strings', () => {
    globalThis.window.__i18n__ = { 'num': 'Value: {val}' };
    assert.equal(t('num', { val: 42 }), 'Value: 42');
  });
});

describe('t() English plural rules', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'en';
    globalThis.window.__i18n__ = {
      'items': '{count, plural, one {# item} other {# items}}',
      'exact': '{count, plural, =0 {no items} one {# item} other {# items}}',
    };
  });

  it('selects "one" for count=1', () => {
    assert.equal(t('items', { count: 1 }), '1 item');
  });

  it('selects "other" for count=0', () => {
    assert.equal(t('items', { count: 0 }), '0 items');
  });

  it('selects "other" for count=5', () => {
    assert.equal(t('items', { count: 5 }), '5 items');
  });

  it('selects "other" for count=21', () => {
    assert.equal(t('items', { count: 21 }), '21 items');
  });

  it('prefers exact match =0 over category', () => {
    assert.equal(t('exact', { count: 0 }), 'no items');
  });

  it('replaces # with the count value', () => {
    assert.equal(t('items', { count: 42 }), '42 items');
  });
});

describe('t() Russian plural rules', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'ru';
    globalThis.window.__i18n__ = {
      'games': '{count, plural, one {# игра} few {# игры} many {# игр} other {# игр}}',
    };
  });

  it('selects "one" for 1', () => {
    assert.equal(t('games', { count: 1 }), '1 игра');
  });

  it('selects "one" for 21', () => {
    assert.equal(t('games', { count: 21 }), '21 игра');
  });

  it('selects "one" for 101', () => {
    assert.equal(t('games', { count: 101 }), '101 игра');
  });

  it('selects "few" for 2', () => {
    assert.equal(t('games', { count: 2 }), '2 игры');
  });

  it('selects "few" for 3', () => {
    assert.equal(t('games', { count: 3 }), '3 игры');
  });

  it('selects "few" for 4', () => {
    assert.equal(t('games', { count: 4 }), '4 игры');
  });

  it('selects "few" for 22', () => {
    assert.equal(t('games', { count: 22 }), '22 игры');
  });

  it('selects "many" for 0', () => {
    assert.equal(t('games', { count: 0 }), '0 игр');
  });

  it('selects "many" for 5', () => {
    assert.equal(t('games', { count: 5 }), '5 игр');
  });

  it('selects "many" for 11', () => {
    assert.equal(t('games', { count: 11 }), '11 игр');
  });

  it('selects "many" for 12', () => {
    assert.equal(t('games', { count: 12 }), '12 игр');
  });

  it('selects "many" for 14', () => {
    assert.equal(t('games', { count: 14 }), '14 игр');
  });

  it('selects "many" for 111', () => {
    assert.equal(t('games', { count: 111 }), '111 игр');
  });
});

describe('t() Polish plural rules', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'pl';
    globalThis.window.__i18n__ = {
      'files': '{count, plural, one {# plik} few {# pliki} many {# plików} other {# plików}}',
    };
  });

  it('selects "one" for 1', () => {
    assert.equal(t('files', { count: 1 }), '1 plik');
  });

  it('selects "few" for 2', () => {
    assert.equal(t('files', { count: 2 }), '2 pliki');
  });

  it('selects "few" for 4', () => {
    assert.equal(t('files', { count: 4 }), '4 pliki');
  });

  it('selects "few" for 22', () => {
    assert.equal(t('files', { count: 22 }), '22 pliki');
  });

  it('selects "many" for 0', () => {
    assert.equal(t('files', { count: 0 }), '0 plików');
  });

  it('selects "many" for 5', () => {
    assert.equal(t('files', { count: 5 }), '5 plików');
  });

  it('selects "many" for 12', () => {
    assert.equal(t('files', { count: 12 }), '12 plików');
  });

  it('selects "many" for 112', () => {
    assert.equal(t('files', { count: 112 }), '112 plików');
  });
});

describe('t() French plural rules', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'fr';
    globalThis.window.__i18n__ = {
      'items': '{count, plural, one {# élément} other {# éléments}}',
    };
  });

  it('selects "one" for 0 (French treats 0 as singular)', () => {
    assert.equal(t('items', { count: 0 }), '0 élément');
  });

  it('selects "one" for 1', () => {
    assert.equal(t('items', { count: 1 }), '1 élément');
  });

  it('selects "other" for 2', () => {
    assert.equal(t('items', { count: 2 }), '2 éléments');
  });
});

describe('t() Chinese plural rules', () => {
  beforeEach(() => {
    globalThis.window.__locale__ = 'zh';
    globalThis.window.__i18n__ = {
      'items': '{count, plural, other {#个项目}}',
    };
  });

  it('always selects "other"', () => {
    assert.equal(t('items', { count: 0 }), '0个项目');
    assert.equal(t('items', { count: 1 }), '1个项目');
    assert.equal(t('items', { count: 42 }), '42个项目');
  });
});

describe('t() unknown locale falls back to English rules', () => {
  it('uses English rules for unknown locale', () => {
    globalThis.window.__locale__ = 'xx';
    globalThis.window.__i18n__ = {
      'items': '{count, plural, one {# item} other {# items}}',
    };
    assert.equal(t('items', { count: 1 }), '1 item');
    assert.equal(t('items', { count: 2 }), '2 items');
  });
});

describe('t() combined plural and placeholders', () => {
  it('resolves plural then placeholders in the same message', () => {
    globalThis.window.__locale__ = 'en';
    globalThis.window.__i18n__ = {
      'summary': '{user} has {count, plural, one {# game} other {# games}}',
    };
    assert.equal(t('summary', { user: 'Alice', count: 1 }), 'Alice has 1 game');
    assert.equal(t('summary', { user: 'Bob', count: 5 }), 'Bob has 5 games');
  });
});
