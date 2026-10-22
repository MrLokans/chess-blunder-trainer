export function safeNext(raw: string | null): string {
  // Only same-origin paths pass. Validate what the browser will actually
  // navigate to: URL parsing strips tabs/newlines and treats `\` as `/`, so
  // `/\t/evil.com` would otherwise become `//evil.com`.
  if (!raw?.startsWith('/')) return '/';
  const url = new URL(raw, window.location.origin);
  if (url.origin !== window.location.origin) return '/';
  return url.pathname + url.search + url.hash;
}
