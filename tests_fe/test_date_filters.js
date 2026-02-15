import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { getPresetDates } from '../blunder_tutor/web/static/js/dashboard/date-filters.js';

describe('getPresetDates', () => {
  it('returns null dates for "all" preset', () => {
    const result = getPresetDates('all');
    assert.equal(result.from, null);
    assert.equal(result.to, null);
  });

  it('returns date strings for "7d" preset', () => {
    const result = getPresetDates('7d');
    assert.ok(result.from);
    assert.ok(result.to);
    const fromDate = new Date(result.from);
    const toDate = new Date(result.to);
    const diffDays = Math.round((toDate - fromDate) / (24 * 60 * 60 * 1000));
    assert.ok(diffDays >= 6 && diffDays <= 7);
  });

  it('returns date strings for "30d" preset', () => {
    const result = getPresetDates('30d');
    assert.ok(result.from);
    const fromDate = new Date(result.from);
    const toDate = new Date(result.to);
    const diffDays = Math.round((toDate - fromDate) / (24 * 60 * 60 * 1000));
    assert.ok(diffDays >= 29 && diffDays <= 30);
  });

  it('returns date strings for "90d" preset', () => {
    const result = getPresetDates('90d');
    assert.ok(result.from);
  });

  it('returns date strings for "1y" preset', () => {
    const result = getPresetDates('1y');
    assert.ok(result.from);
    const fromDate = new Date(result.from);
    const toDate = new Date(result.to);
    const diffDays = Math.round((toDate - fromDate) / (24 * 60 * 60 * 1000));
    assert.ok(diffDays >= 364 && diffDays <= 366);
  });

  it('returns null from for unknown presets', () => {
    const result = getPresetDates('unknown');
    assert.equal(result.from, null);
  });
});
