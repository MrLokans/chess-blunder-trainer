export function useFeature(name: string): boolean {
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
  const features = window.__features ?? {};
  return features[name] !== false;
}
