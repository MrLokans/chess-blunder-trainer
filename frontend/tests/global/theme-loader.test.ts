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
      expect(root.style.getPropertyValue('--color-success')).toBe('#abcdef');
    });

    expect(root.style.getPropertyValue('--color-primary')).toBe('#123456');
    expect(localStorage.getItem('theme')).toBe(JSON.stringify({ success: '#abcdef' }));
  });
});
