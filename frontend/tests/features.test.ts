import { describe, it, expect, beforeEach } from 'vitest';
import { hasFeature } from '../src/shared/features';

describe('hasFeature', () => {
  beforeEach(() => {
    window.__features = {};
  });

  it('returns true for undefined feature (opt-out model)', () => {
    expect(hasFeature('some.feature')).toBe(true);
  });

  it('returns true when feature is explicitly true', () => {
    window.__features = { 'my.feature': true };
    expect(hasFeature('my.feature')).toBe(true);
  });

  it('returns false when feature is explicitly false', () => {
    window.__features = { 'my.feature': false };
    expect(hasFeature('my.feature')).toBe(false);
  });

  it('returns true when __features is not set at all', () => {
    delete window.__features;
    expect(hasFeature('anything')).toBe(true);
  });

  it('returns true for truthy non-boolean values', () => {
    window.__features = { 'my.feature': 'yes' };
    expect(hasFeature('my.feature')).toBe(true);
  });

  it('returns true for zero (0 !== false)', () => {
    window.__features = { 'my.feature': 0 };
    expect(hasFeature('my.feature')).toBe(true);
  });

  it('returns true for null (null !== false)', () => {
    window.__features = { 'my.feature': null };
    expect(hasFeature('my.feature')).toBe(true);
  });
});
