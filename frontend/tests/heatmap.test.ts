import { describe, it, expect } from 'vitest';
import { getActivityLevel } from '../src/heatmap';

describe('getActivityLevel', () => {
  it('returns 0 for no activity', () => {
    expect(getActivityLevel(0)).toBe(0);
  });

  it('returns 1 for 1-4 puzzles', () => {
    expect(getActivityLevel(1)).toBe(1);
    expect(getActivityLevel(4)).toBe(1);
  });

  it('returns 2 for 5-9 puzzles', () => {
    expect(getActivityLevel(5)).toBe(2);
    expect(getActivityLevel(9)).toBe(2);
  });

  it('returns 3 for 10-19 puzzles', () => {
    expect(getActivityLevel(10)).toBe(3);
    expect(getActivityLevel(19)).toBe(3);
  });

  it('returns 4 for 20+ puzzles', () => {
    expect(getActivityLevel(20)).toBe(4);
    expect(getActivityLevel(100)).toBe(4);
  });
});
