import { describe, it, expect } from 'vitest';
import { safeNext } from '../../src/auth/LoginForm';

describe('safeNext', () => {
  it('returns / for null', () => {
    expect(safeNext(null)).toBe('/');
  });

  it('returns / for empty string', () => {
    expect(safeNext('')).toBe('/');
  });

  it('accepts absolute same-origin paths', () => {
    expect(safeNext('/trainer')).toBe('/trainer');
    expect(safeNext('/dashboard?foo=bar')).toBe('/dashboard?foo=bar');
  });

  it('rejects protocol-relative URLs', () => {
    expect(safeNext('//evil.com')).toBe('/');
    expect(safeNext('//evil.com/path')).toBe('/');
  });

  it('rejects absolute URLs', () => {
    expect(safeNext('https://evil.com')).toBe('/');
    expect(safeNext('http://evil.com/path')).toBe('/');
  });

  it('rejects backslash-prefixed variants', () => {
    expect(safeNext('/\\evil.com')).toBe('/');
  });

  it('rejects schemeless paths without leading slash', () => {
    expect(safeNext('trainer')).toBe('/');
    expect(safeNext('evil.com')).toBe('/');
  });
});
