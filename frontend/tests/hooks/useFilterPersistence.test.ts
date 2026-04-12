import { describe, test, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/preact';
import { useFilterPersistence } from '../../src/hooks/useFilterPersistence';

describe('useFilterPersistence', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  test('returns default values when nothing stored', () => {
    const defaults = ['bullet', 'blitz', 'rapid'];
    const { result } = renderHook(() => useFilterPersistence('test-filters', defaults));
    expect(result.current[0]).toEqual(defaults);
  });

  test('loads stored values from localStorage', () => {
    localStorage.setItem('test-filters', JSON.stringify(['blitz']));
    const { result } = renderHook(() => useFilterPersistence('test-filters', ['bullet', 'blitz']));
    expect(result.current[0]).toEqual(['blitz']);
  });

  test('persists values to localStorage on update', async () => {
    const { result } = renderHook(() => useFilterPersistence('test-filters', ['bullet', 'blitz']));

    await act(() => {
      result.current[1](['rapid', 'classical']);
    });

    expect(result.current[0]).toEqual(['rapid', 'classical']);
    const stored = localStorage.getItem('test-filters');
    expect(JSON.parse(stored ?? '[]')).toEqual(['rapid', 'classical']);
  });

  test('falls back to defaults on corrupt stored data', () => {
    localStorage.setItem('test-filters', 'not-json{{{');
    const defaults = ['bullet', 'blitz'];
    const { result } = renderHook(() => useFilterPersistence('test-filters', defaults));
    expect(result.current[0]).toEqual(defaults);
  });

  test('falls back to defaults when stored value is not an array', () => {
    localStorage.setItem('test-filters', JSON.stringify({ not: 'array' }));
    const defaults = ['bullet'];
    const { result } = renderHook(() => useFilterPersistence('test-filters', defaults));
    expect(result.current[0]).toEqual(defaults);
  });
});
