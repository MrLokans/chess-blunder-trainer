import { afterEach, describe, expect, it, vi } from 'vitest';

const root = document.documentElement;

afterEach(() => {
  localStorage.clear();
  root.removeAttribute('style');
  root.removeAttribute('data-theme');
  vi.unstubAllGlobals();
  vi.resetModules();
});

interface MockMediaQuery {
  matches: boolean;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
}

function mockMediaQuery(matches = false): MockMediaQuery {
  const media = {
    matches,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };
  vi.stubGlobal('matchMedia', vi.fn().mockReturnValue(media));
  return media;
}

describe('theme loader', () => {
  it('applies cached colours and synchronizes the server theme', async () => {
    localStorage.setItem('theme', JSON.stringify({ primary: '#123456' }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: '#abcdef' }),
    }));

    await import('../../src/global/theme-loader');
    await vi.waitFor(() => {
      expect(root.style.getPropertyValue('--user-success')).toBe('#abcdef');
    });

    expect(root.style.getPropertyValue('--user-accent')).toBe('');
    expect(localStorage.getItem('theme')).toBe(JSON.stringify({ success: '#abcdef' }));
  });

  it('removes stale custom properties before applying a theme', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));
    const { applyTheme, removeTheme } = await import('../../src/global/theme-loader');

    applyTheme({ primary: '#123456' });
    applyTheme({ success: '#abcdef' });

    expect(root.style.getPropertyValue('--user-accent')).toBe('');
    expect(root.style.getPropertyValue('--user-success')).toBe('#abcdef');
    removeTheme();
    expect(root.style.getPropertyValue('--user-success')).toBe('');
  });

  it('discards invalid cached colors', async () => {
    localStorage.setItem('theme', JSON.stringify({ primary: 'blue' }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));

    await import('../../src/global/theme-loader');

    expect(root.style.getPropertyValue('--user-accent')).toBe('');
  });

  it('ignores a failed theme response instead of wiping custom colours', async () => {
    localStorage.setItem('theme', JSON.stringify({ primary: '#123456' }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'boom' }),
    }));

    await import('../../src/global/theme-loader');
    await vi.waitFor(() => {
      expect(root.style.getPropertyValue('--user-accent')).toBe('#123456');
    });

    expect(localStorage.getItem('theme')).toBe(JSON.stringify({ primary: '#123456' }));
  });

  it('dispatches themechange only when the server theme differs from the cache', async () => {
    const cached = JSON.stringify({ primary: '#123456' });
    localStorage.setItem('theme', cached);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(JSON.parse(cached)) }));
    const onThemeChange = vi.fn();
    window.addEventListener('themechange', onThemeChange);

    await import('../../src/global/theme-loader');
    await vi.waitFor(() => {
      expect(root.style.getPropertyValue('--user-accent')).toBe('#123456');
    });

    expect(onThemeChange).not.toHaveBeenCalled();
    window.removeEventListener('themechange', onThemeChange);
  });

  it('applies explicit mode and dispatches themechange', async () => {
    localStorage.setItem('theme-mode', 'light');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));
    const { syncThemeMode } = await import('../../src/global/theme-loader');
    const onThemeChange = vi.fn();
    window.addEventListener('themechange', onThemeChange);

    localStorage.setItem('theme-mode', 'dark');
    syncThemeMode();

    expect(root.dataset.theme).toBe('dark');
    expect(onThemeChange).toHaveBeenCalledWith(expect.objectContaining({
      detail: { mode: 'dark', effectiveMode: 'dark' },
    }));
  });

  it('uses system mode and responds to OS changes only in system mode', async () => {
    const media = mockMediaQuery(true);
    localStorage.setItem('theme-mode', 'invalid');
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({}) }));
    const { syncThemeMode } = await import('../../src/global/theme-loader');

    expect(root.dataset.theme).toBeUndefined();
    expect(localStorage.getItem('theme-mode')).toBeNull();
    const listener = media.addEventListener.mock.calls[0]?.[1] as (() => void);
    const onThemeChange = vi.fn();
    window.addEventListener('themechange', onThemeChange);
    media.matches = false;
    listener();

    expect(onThemeChange).toHaveBeenCalledWith(expect.objectContaining({
      detail: { mode: 'system', effectiveMode: 'light' },
    }));
    localStorage.setItem('theme-mode', 'dark');
    syncThemeMode();
    expect(media.removeEventListener).toHaveBeenCalled();
  });
});
