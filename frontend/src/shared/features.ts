export function hasFeature(name: string): boolean {
  return (window.__features ?? {})[name] !== false;
}
