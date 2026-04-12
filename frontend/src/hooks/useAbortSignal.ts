import { useRef, useCallback } from 'preact/hooks';

export function useAbortSignal(): () => AbortSignal {
  const controllerRef = useRef<AbortController | null>(null);

  return useCallback(() => {
    if (controllerRef.current) {
      controllerRef.current.abort();
    }
    controllerRef.current = new AbortController();
    return controllerRef.current.signal;
  }, []);
}
