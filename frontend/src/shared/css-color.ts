export function readColorToken(name: string, fallback: string): string {
  const probe = document.createElement('span');
  probe.style.color = `var(${name})`;
  document.documentElement.append(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return color || fallback;
}
