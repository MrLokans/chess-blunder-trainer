import { describe, it, beforeEach } from 'node:test';
import assert from 'node:assert/strict';

globalThis.window = globalThis.window || {};

const { hasFeature } = await import('../blunder_tutor/web/static/js/features.js');

describe('hasFeature', () => {
  beforeEach(() => {
    globalThis.window.__features = {};
  });

  it('returns true for undefined feature (opt-out model)', () => {
    assert.equal(hasFeature('some.feature'), true);
  });

  it('returns true when feature is explicitly true', () => {
    globalThis.window.__features = { 'my.feature': true };
    assert.equal(hasFeature('my.feature'), true);
  });

  it('returns false when feature is explicitly false', () => {
    globalThis.window.__features = { 'my.feature': false };
    assert.equal(hasFeature('my.feature'), false);
  });

  it('returns true when __features is not set at all', () => {
    delete globalThis.window.__features;
    assert.equal(hasFeature('anything'), true);
  });

  it('returns true for truthy non-boolean values', () => {
    globalThis.window.__features = { 'my.feature': 'yes' };
    assert.equal(hasFeature('my.feature'), true);
  });

  it('returns true for zero (0 !== false)', () => {
    globalThis.window.__features = { 'my.feature': 0 };
    assert.equal(hasFeature('my.feature'), true);
  });

  it('returns true for null (null !== false)', () => {
    globalThis.window.__features = { 'my.feature': null };
    assert.equal(hasFeature('my.feature'), true);
  });
});
