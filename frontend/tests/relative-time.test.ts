import { describe, test, expect } from 'vitest';
import { formatRelativeAgo } from '../src/shared/relative-time';

const NOW = new Date('2026-05-01T12:00:00Z');

describe('formatRelativeAgo', () => {
  test('< 60s reports "just now"', () => {
    const ts = new Date(NOW.getTime() - 30_000).toISOString();
    expect(formatRelativeAgo(ts, NOW)).toBe('time.just_now');
  });

  test('minutes ago, ICU plural string forwarded with count', () => {
    const ts = new Date(NOW.getTime() - 5 * 60_000).toISOString();
    expect(formatRelativeAgo(ts, NOW)).toBe('time.minutes_ago[count=5]');
  });

  test('hours ago', () => {
    const ts = new Date(NOW.getTime() - 3 * 60 * 60_000).toISOString();
    expect(formatRelativeAgo(ts, NOW)).toBe('time.hours_ago[count=3]');
  });

  test('days ago', () => {
    const ts = new Date(NOW.getTime() - 2 * 24 * 60 * 60_000).toISOString();
    expect(formatRelativeAgo(ts, NOW)).toBe('time.days_ago[count=2]');
  });

  test('past one week → falls back to a locale date string', () => {
    const ts = new Date(NOW.getTime() - 14 * 24 * 60 * 60_000).toISOString();
    const out = formatRelativeAgo(ts, NOW);
    expect(out).not.toContain('time.');
    expect(out.length).toBeGreaterThan(0);
  });

  test('future timestamps clamp to "just now" rather than negative counts', () => {
    const ts = new Date(NOW.getTime() + 1000).toISOString();
    expect(formatRelativeAgo(ts, NOW)).toBe('time.just_now');
  });
});
