export function hasFeature(name: string): boolean {
  const features = window.__features as Record<string, boolean> | undefined;
  if (!features) return true;
  return features[name] !== false;
}
