import { vi, afterEach } from 'vitest';
import { cleanup } from '@testing-library/preact';

afterEach(() => {
  cleanup();
});

// Mock vendored globals that would normally be loaded via script in base.html
vi.stubGlobal('Chess', undefined);
vi.stubGlobal('htmx', undefined);
vi.stubGlobal('Chart', undefined);

// Mock i18n globals. The `t` stub mirrors production's two-argument
// shape — a callsite that forgets to pass `params` for a key with
// `{placeholder}` substitutions would render the literal placeholder
// text alongside any JSX-concatenated values (the `dashboard.analysis.
// running` regression). Returning the params in the rendered string
// means assertions against `t(key, params)` exercise the same path
// the production component does.
vi.stubGlobal('t', (key: string, params?: Record<string, unknown>) => {
  if (!params) return key;
  const parts = Object.entries(params)
    .map(([k, v]) => `${k}=${String(v)}`)
    .join(',');
  return `${key}[${parts}]`;
});
vi.stubGlobal('trackEvent', vi.fn());
vi.stubGlobal('formatNumber', (n: number) => String(n));
vi.stubGlobal('formatDate', (d: unknown) => String(d));
