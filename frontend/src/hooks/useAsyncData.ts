import { useState, useEffect, useCallback, useRef } from 'preact/hooks';
import { useAbortSignal } from './useAbortSignal';
import { translateApiErrorToMessage } from '../shared/translate-api-error';

export interface AsyncDataState<T> {
  loading: boolean;
  error: string | null;
  data: T | null;
  reload: () => void;
}

export function useAsyncData<T>(
  fetcher: (signal: AbortSignal) => Promise<T>,
  deps: unknown[],
): AsyncDataState<T> {
  const nextSignal = useAbortSignal();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<T | null>(null);
  const [nonce, setNonce] = useState(0);

  // Callers pass an inline closure that changes identity every render. The
  // explicit `deps` array (plus `reload`) is the re-fetch key; the latest
  // closure is read through a ref so it never forces a stale-deps re-fetch.
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const reload = useCallback(() => {
    setNonce((n) => n + 1);
  }, []);

  useEffect(() => {
    // `nextSignal()` aborts the controller from the previous run, so a deps
    // change cancels the in-flight request before starting a new one.
    const signal = nextSignal();
    setLoading(true);
    setError(null);

    void (async () => {
      try {
        const result = await fetcherRef.current(signal);
        if (signal.aborted) return;
        setData(result);
      } catch (err) {
        if (signal.aborted) return;
        if (err instanceof DOMException && err.name === 'AbortError') return;
        setData(null);
        setError(translateApiErrorToMessage(err));
      } finally {
        if (!signal.aborted) setLoading(false);
      }
    })();

    return () => {
      nextSignal();
    };
  }, [nextSignal, nonce, ...deps]);

  return { loading, error, data, reload };
}
