import { describe, it, expect } from 'vitest';
import { getPresetDates } from '../../src/dashboard/date-filters';

describe('getPresetDates', () => {
  it('returns null dates for "all" preset', () => {
    const result = getPresetDates('all');
    expect(result.from).toBeNull();
    expect(result.to).toBeNull();
  });

  it('returns date strings for "7d" preset', () => {
    const result = getPresetDates('7d');
    expect(result.from).toBeTruthy();
    expect(result.to).toBeTruthy();
    const fromDate = new Date(result.from!);
    const toDate = new Date(result.to!);
    const diffDays = Math.round((toDate.getTime() - fromDate.getTime()) / (24 * 60 * 60 * 1000));
    expect(diffDays).toBeGreaterThanOrEqual(6);
    expect(diffDays).toBeLessThanOrEqual(7);
  });

  it('returns date strings for "30d" preset', () => {
    const result = getPresetDates('30d');
    expect(result.from).toBeTruthy();
    const fromDate = new Date(result.from!);
    const toDate = new Date(result.to!);
    const diffDays = Math.round((toDate.getTime() - fromDate.getTime()) / (24 * 60 * 60 * 1000));
    expect(diffDays).toBeGreaterThanOrEqual(29);
    expect(diffDays).toBeLessThanOrEqual(30);
  });

  it('returns date strings for "90d" preset', () => {
    const result = getPresetDates('90d');
    expect(result.from).toBeTruthy();
  });

  it('returns date strings for "1y" preset', () => {
    const result = getPresetDates('1y');
    expect(result.from).toBeTruthy();
    const fromDate = new Date(result.from!);
    const toDate = new Date(result.to!);
    const diffDays = Math.round((toDate.getTime() - fromDate.getTime()) / (24 * 60 * 60 * 1000));
    expect(diffDays).toBeGreaterThanOrEqual(364);
    expect(diffDays).toBeLessThanOrEqual(366);
  });

  it('returns null from for unknown presets', () => {
    const result = getPresetDates('unknown');
    expect(result.from).toBeNull();
  });
});
