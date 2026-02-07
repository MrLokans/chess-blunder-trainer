export function hasFeature(name) {
  return (window.__features || {})[name] !== false;
}
