import { describe, test, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/preact';
import { useReviewQueue } from '../../src/trainer/hooks/useReviewQueue';
import { client } from '../../src/shared/api';

vi.mock('../../src/shared/api', () => ({
  client: {
    srs: {
      status: vi.fn(),
      next: vi.fn(),
    },
  },
}));

const statusMock = vi.mocked(client.srs.status);

describe('useReviewQueue', () => {
  beforeEach(() => {
    statusMock.mockReset();
    statusMock.mockResolvedValue({ due: 3, active: 5, next_due_at: '2026-07-08T00:00:00Z' });
  });

  test('disabled: never fetches, dueCount stays 0', async () => {
    const { result } = renderHook(() => useReviewQueue(false));
    await waitFor(() => { expect(result.current.dueCount).toBe(0); });
    expect(statusMock).not.toHaveBeenCalled();
  });

  test('enabled: fetches status on mount', async () => {
    const { result } = renderHook(() => useReviewQueue(true));
    await waitFor(() => { expect(result.current.dueCount).toBe(3); });
    expect(result.current.status?.active).toBe(5);
  });

  test('startSession snapshots total from dueCount', async () => {
    const { result } = renderHook(() => useReviewQueue(true));
    await waitFor(() => { expect(result.current.dueCount).toBe(3); });

    await act(() => { result.current.startSession(); });

    expect(result.current.session).toEqual({ total: 3, done: 0 });
  });

  test('recordResult increments done', async () => {
    const { result } = renderHook(() => useReviewQueue(true));
    await waitFor(() => { expect(result.current.dueCount).toBe(3); });

    await act(() => { result.current.startSession(); });
    await act(() => { result.current.recordResult(); });

    expect(result.current.session).toEqual({ total: 3, done: 1 });
  });

  test('recordResult re-fetches status so due count tracks the server', async () => {
    const { result } = renderHook(() => useReviewQueue(true));
    await waitFor(() => { expect(result.current.dueCount).toBe(3); });

    statusMock.mockResolvedValue({ due: 2, active: 5, next_due_at: '2026-07-09T00:00:00Z' });
    await act(() => { result.current.startSession(); });
    await act(() => { result.current.recordResult(); });

    await waitFor(() => { expect(result.current.dueCount).toBe(2); });
  });

  test('syncs the nav badge element with the due count', async () => {
    const badge = document.createElement('span');
    badge.id = 'srsNavBadge';
    badge.hidden = true;
    document.body.appendChild(badge);
    try {
      const { result } = renderHook(() => useReviewQueue(true));
      await waitFor(() => { expect(result.current.dueCount).toBe(3); });
      expect(badge.textContent).toBe('3');
      expect(badge.hidden).toBe(false);

      statusMock.mockResolvedValue({ due: 0, active: 5, next_due_at: null });
      await act(() => { result.current.startSession(); });
      await act(() => { result.current.recordResult(); });

      await waitFor(() => { expect(badge.hidden).toBe(true); });
    } finally {
      badge.remove();
    }
  });

  test('endSession clears session and re-fetches status', async () => {
    const { result } = renderHook(() => useReviewQueue(true));
    await waitFor(() => { expect(result.current.dueCount).toBe(3); });

    await act(() => { result.current.startSession(); });
    statusMock.mockResolvedValue({ due: 0, active: 5, next_due_at: null });
    await act(() => { result.current.endSession(); });

    expect(result.current.session).toBeNull();
    await waitFor(() => { expect(result.current.dueCount).toBe(0); });
  });

  test('status fetch failure degrades to zero due', async () => {
    statusMock.mockRejectedValue(new Error('offline'));
    const { result } = renderHook(() => useReviewQueue(true));
    await waitFor(() => { expect(statusMock).toHaveBeenCalled(); });
    expect(result.current.dueCount).toBe(0);
    expect(result.current.status).toBeNull();
  });
});
