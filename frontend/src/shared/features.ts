export function hasFeature(name: string): boolean {
  const features = window.__features;
  if (!features) return true;
  return features[name] !== false;
}
