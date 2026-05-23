export function safeNext(raw: string | null): string {
  // Reject absolute/protocol-relative URLs so `?next=//evil.com` or
  // `?next=https://evil.com` can't bounce the user off-origin after
  // login. Only same-origin paths pass.
  if (!raw) return '/';
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) {
    return '/';
  }
  return raw;
}
