import { vi } from 'vitest';

// Mock vendored globals that would normally be loaded via script in base.html
vi.stubGlobal('Chess', undefined);
vi.stubGlobal('htmx', undefined);
vi.stubGlobal('Chart', undefined);

// Mock i18n globals
vi.stubGlobal('t', (key: string) => key);
vi.stubGlobal('trackEvent', vi.fn());
vi.stubGlobal('formatNumber', (n: number) => String(n));
vi.stubGlobal('formatDate', (d: unknown) => String(d));
