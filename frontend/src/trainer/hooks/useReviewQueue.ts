import { useCallback, useEffect, useState } from 'preact/hooks';
import { client } from '../../shared/api';
import type { SrsStatusResponse } from '../../types/api';

export interface ReviewSession { total: number; done: number }

export interface ReviewQueueAPI {
  status: SrsStatusResponse | null;
  dueCount: number;
  session: ReviewSession | null;
  refresh: () => Promise<void>;
  startSession: () => void;
  recordResult: () => void;
  endSession: () => void;
}

export function useReviewQueue(enabled: boolean): ReviewQueueAPI {
  const [status, setStatus] = useState<SrsStatusResponse | null>(null);
  const [session, setSession] = useState<ReviewSession | null>(null);
  const dueCount = status?.due ?? 0;

  const refresh = useCallback(async () => {
    if (!enabled) return;
    try {
      setStatus(await client.srs.status());
    } catch {
      setStatus(null);
    }
  }, [enabled]);

  useEffect(() => { void refresh(); }, [refresh]);

  // The nav badge is server-rendered and pre-filled by static/js/srs-badge.js
  // on page load; once the trainer island is live, this hook owns it so the
  // count tracks reviews completed within the session.
  useEffect(() => {
    if (!enabled || status === null) return;
    const badge = document.getElementById('srsNavBadge');
    if (!badge) return;
    badge.textContent = status.due > 0 ? String(status.due) : '';
    badge.hidden = status.due <= 0;
  }, [enabled, status]);

  const startSession = useCallback(() => {
    setSession({ total: dueCount, done: 0 });
  }, [dueCount]);

  const recordResult = useCallback(() => {
    setSession((current) => current && { ...current, done: current.done + 1 });
    void refresh();
  }, [refresh]);

  const endSession = useCallback(() => {
    setSession(null);
    void refresh();
  }, [refresh]);

  return { status, dueCount, session, refresh, startSession, recordResult, endSession };
}
