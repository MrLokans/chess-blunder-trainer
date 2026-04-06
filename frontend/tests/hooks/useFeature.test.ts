import { describe, test, expect, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/preact';
import { useFeature } from '../../src/hooks/useFeature';

describe('useFeature', () => {
  beforeEach(() => {
    window.__features = {};
  });

  test('returns true when feature is enabled', () => {
    window.__features = { 'trainer.pre_move': true };
    const { result } = renderHook(() => useFeature('trainer.pre_move'));
    expect(result.current).toBe(true);
  });

  test('returns true when feature is not explicitly set (default enabled)', () => {
    window.__features = {};
    const { result } = renderHook(() => useFeature('trainer.pre_move'));
    expect(result.current).toBe(true);
  });

  test('returns false when feature is explicitly disabled', () => {
    window.__features = { 'debug.copy': false };
    const { result } = renderHook(() => useFeature('debug.copy'));
    expect(result.current).toBe(false);
  });

  test('returns true when __features is undefined', () => {
    window.__features = undefined;
    const { result } = renderHook(() => useFeature('anything'));
    expect(result.current).toBe(true);
  });
});
