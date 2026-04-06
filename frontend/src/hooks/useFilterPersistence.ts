import { useState, useCallback } from 'preact/hooks';

function loadFromStorage(key: string, defaults: string[]): string[] {
  const stored = localStorage.getItem(key);
  if (!stored) return defaults;

  try {
    const parsed: unknown = JSON.parse(stored);
    return Array.isArray(parsed) ? parsed as string[] : defaults;
  } catch {
    return defaults;
  }
}

export function useFilterPersistence(
  key: string,
  defaults: string[],
): [string[], (values: string[]) => void] {
  const [values, setValuesState] = useState(() => loadFromStorage(key, defaults));

  const setValues = useCallback((newValues: string[]) => {
    setValuesState(newValues);
    localStorage.setItem(key, JSON.stringify(newValues));
  }, [key]);

  return [values, setValues];
}
