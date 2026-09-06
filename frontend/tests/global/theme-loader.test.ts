import { afterEach, describe, expect, it, vi } from 'vitest';

const root = document.documentElement;

afterEach(() => {
  localStorage.clear();
  root.removeAttribute('style');
  vi.unstubAllGlobals();
  vi.resetModules();
});

describe('theme loader', () => {
  it('applies cached colours and synchronizes the server theme', async () => {
    localStorage.setItem('theme', JSON.stringify({ primary: '#123456' }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
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
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ json: () => Promise.resolve({}) }));
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
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ json: () => Promise.resolve({}) }));

    await import('../../src/global/theme-loader');

    expect(root.style.getPropertyValue('--user-accent')).toBe('');
  });
});
