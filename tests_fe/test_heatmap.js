import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { setupGlobalDOM } from './helpers/dom.js';

setupGlobalDOM();

const { getActivityLevel } = await import('../blunder_tutor/web/static/js/heatmap.js');

describe('getActivityLevel', () => {
  it('returns 0 for no activity', () => {
    assert.equal(getActivityLevel(0), 0);
  });

  it('returns 1 for 1-4 puzzles', () => {
    assert.equal(getActivityLevel(1), 1);
    assert.equal(getActivityLevel(4), 1);
  });

  it('returns 2 for 5-9 puzzles', () => {
    assert.equal(getActivityLevel(5), 2);
    assert.equal(getActivityLevel(9), 2);
  });

  it('returns 3 for 10-19 puzzles', () => {
    assert.equal(getActivityLevel(10), 3);
    assert.equal(getActivityLevel(19), 3);
  });

  it('returns 4 for 20+ puzzles', () => {
    assert.equal(getActivityLevel(20), 4);
    assert.equal(getActivityLevel(100), 4);
  });
});
