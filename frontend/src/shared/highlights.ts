export type HighlightMap = Map<string, string>;

export function mergeHighlights(...maps: HighlightMap[]): HighlightMap {
  const merged: HighlightMap = new Map();
  for (const map of maps) {
    for (const [key, value] of map) {
      const existing = merged.get(key);
      merged.set(key, existing ? existing + ' ' + value : value);
    }
  }
  return merged;
}
