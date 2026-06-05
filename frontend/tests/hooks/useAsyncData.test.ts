import { describe, test, expect, vi } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/preact';
import { useAsyncData } from '../../src/hooks/useAsyncData';
import { ApiError } from '../../src/shared/api';

describe('useAsyncData', () => {
  test('resolves to data', async () => {
    const fetcher = vi.fn().mockResolvedValue({ value: 42 });
    const { result } = renderHook(() => useAsyncData(fetcher, []));

    expect(result.current.loading).toBe(true);
    await waitFor(() => { expect(result.current.loading).toBe(false); });

    expect(result.current.data).toEqual({ value: 42 });
    expect(result.current.error).toBeNull();
  });

  test('maps a rejection to an error string', async () => {
    const fetcher = vi.fn().mockRejectedValue(new ApiError(500, 'boom'));
    const { result } = renderHook(() => useAsyncData(fetcher, []));

    await waitFor(() => { expect(result.current.loading).toBe(false); });

    expect(result.current.error).toBe('boom');
    expect(result.current.data).toBeNull();
  });

  test('falls back to a generic message for a non-error rejection', async () => {
    const fetcher = vi.fn().mockRejectedValue('weird');
    const { result } = renderHook(() => useAsyncData(fetcher, []));

    await waitFor(() => { expect(result.current.loading).toBe(false); });

    expect(result.current.error).toBe('common.error_unknown');
  });

  test('passes an AbortSignal to the fetcher', async () => {
    const fetcher = vi.fn().mockResolvedValue(null);
    renderHook(() => useAsyncData(fetcher, []));

    await waitFor(() => { expect(fetcher).toHaveBeenCalled(); });
    const signalArg: unknown = fetcher.mock.calls[0]?.[0];
    expect(signalArg).toBeInstanceOf(AbortSignal);
  });

  test('aborts the in-flight request on unmount', async () => {
    const signals: AbortSignal[] = [];
    const fetcher = vi.fn((signal: AbortSignal) => {
      signals.push(signal);
      return new Promise<number>(() => { /* never resolves */ });
    });
    const { unmount } = renderHook(() => useAsyncData(fetcher, []));

    await waitFor(() => { expect(signals.length).toBeGreaterThan(0); });
    const signal = signals[0];
    expect(signal?.aborted).toBe(false);
    unmount();
    expect(signal?.aborted).toBe(true);
  });

  test('reload refetches', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce('first')
      .mockResolvedValueOnce('second');
    const { result } = renderHook(() => useAsyncData(fetcher, []));

    await waitFor(() => { expect(result.current.data).toBe('first'); });

    void act(() => {
      result.current.reload();
    });
    await waitFor(() => { expect(result.current.data).toBe('second'); });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  test('refetches when deps change', async () => {
    const fetcher = vi.fn()
      .mockResolvedValueOnce('a')
      .mockResolvedValueOnce('b');
    let dep = 1;
    const { result, rerender } = renderHook(() => useAsyncData(fetcher, [dep]));

    await waitFor(() => { expect(result.current.data).toBe('a'); });

    dep = 2;
    rerender();
    await waitFor(() => { expect(result.current.data).toBe('b'); });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
