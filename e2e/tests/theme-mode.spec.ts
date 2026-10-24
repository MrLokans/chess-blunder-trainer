import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';

const LIGHT_SURFACE = 'rgb(245, 242, 235)';
const DARK_SURFACE = 'rgb(22, 21, 15)';
const CUSTOM_SURFACE = 'rgb(18, 52, 86)';

// Mirrors DEFAULT_THEME in web/api/_settings_schemas.py; Settings needs the full set.
const DEFAULT_THEME = {
  primary: '#1A3A8F', success: '#2D8F3E', error: '#D42828', warning: '#F2C12E',
  phase_opening: '#1A3A8F', phase_middlegame: '#F2C12E', phase_endgame: '#3A3A3A',
  bg: '#F5F2EB', bg_card: '#F5F2EB', text: '#1A1A1A', text_muted: '#3A3A3A',
  heatmap_empty: '#E8E4DB', heatmap_l1: '#B8D9CA', heatmap_l2: '#5BAA7D',
  heatmap_l3: '#2D8F3E', heatmap_l4: '#1A6B2A',
};

interface ThemeSnapshot {
  attr: string | null;
  surface: string;
  pieceWhite: string;
}

declare global {
  interface Window {
    __firstTheme?: ThemeSnapshot;
    __themeEvents?: unknown[];
    __readTheme?: () => ThemeSnapshot;
  }
}

async function prepare(page: Page, storage: Record<string, string> = {}, custom: object = {}): Promise<void> {
  const theme = { ...DEFAULT_THEME, ...custom };
  await page.route('**/api/settings/theme', route => route.fulfill({ json: theme }));
  // A cache matching the server keeps the post-load theme sync from emitting its own themechange.
  const seed = { theme: JSON.stringify(theme), ...storage };
  await page.addInitScript(seed => {
    // Seeds storage on the first document only, so reload tests see what the page persisted.
    if (!sessionStorage.getItem('seeded')) {
      localStorage.clear();
      for (const [key, value] of Object.entries(seed)) localStorage.setItem(key, value);
      sessionStorage.setItem('seeded', '1');
    }
    window.__readTheme = () => {
      const probe = document.createElement('div');
      document.body.append(probe);
      probe.style.color = 'var(--surface)';
      const surface = getComputedStyle(probe).color;
      probe.style.color = 'var(--piece-white)';
      const pieceWhite = getComputedStyle(probe).color;
      probe.remove();
      return { attr: document.documentElement.getAttribute('data-theme'), surface, pieceWhite };
    };
    window.__themeEvents = [];
    window.addEventListener('themechange', event => {
      window.__themeEvents?.push((event as CustomEvent).detail);
    });
    // The loader is a blocking head script, so the theme must already be right at
    // DOMContentLoaded, before any frame could paint the wrong palette.
    document.addEventListener('DOMContentLoaded', () => {
      window.__firstTheme = window.__readTheme?.();
    });
  }, seed);
}

const readTheme = (page: Page) => page.evaluate(() => window.__readTheme?.());
const firstTheme = (page: Page) => page.evaluate(() => window.__firstTheme);
const themeEvents = (page: Page) => page.evaluate(() => window.__themeEvents);

const MATRIX = [
  { os: 'light', stored: null, attr: null, surface: LIGHT_SURFACE },
  { os: 'dark', stored: null, attr: null, surface: DARK_SURFACE },
  { os: 'dark', stored: 'light', attr: 'light', surface: LIGHT_SURFACE },
  { os: 'light', stored: 'dark', attr: 'dark', surface: DARK_SURFACE },
  { os: 'dark', stored: 'sepia', attr: null, surface: DARK_SURFACE },
] as const;

for (const { os, stored, attr, surface } of MATRIX) {
  test(`OS ${os} with stored mode ${stored ?? 'absent'} paints ${surface}`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: os });
    await prepare(page, stored ? { 'theme-mode': stored } : {});
    await page.goto('/settings');

    const first = await firstTheme(page);
    expect(first).toMatchObject({ attr, surface });
    if (stored === 'sepia') {
      expect(await page.evaluate(() => localStorage.getItem('theme-mode'))).toBeNull();
    }
  });
}

test('system mode follows live OS changes and redraws; explicit mode ignores them', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await prepare(page);
  await page.goto('/settings');

  await page.emulateMedia({ colorScheme: 'dark' });
  await expect.poll(() => themeEvents(page)).toEqual([{ mode: 'system', effectiveMode: 'dark' }]);
  expect(await readTheme(page)).toMatchObject({ attr: null, surface: DARK_SURFACE });

  await page.locator('input[name="theme-mode"][value="light"]').check();
  await page.emulateMedia({ colorScheme: 'light' });
  await page.emulateMedia({ colorScheme: 'dark' });
  expect(await readTheme(page)).toMatchObject({ attr: 'light', surface: LIGHT_SURFACE });
  expect(await themeEvents(page)).toEqual([
    { mode: 'system', effectiveMode: 'dark' },
    { mode: 'light', effectiveMode: 'light' },
  ]);
});

test('choosing a mode in Settings applies immediately and persists across reload', async ({ page }) => {
  await page.emulateMedia({ colorScheme: 'light' });
  await prepare(page);
  await page.goto('/settings');

  await page.locator('input[name="theme-mode"][value="dark"]').check();
  expect(await readTheme(page)).toMatchObject({ attr: 'dark', surface: DARK_SURFACE });
  expect(await themeEvents(page)).toEqual([{ mode: 'dark', effectiveMode: 'dark' }]);

  await page.reload();
  expect(await firstTheme(page)).toMatchObject({ attr: 'dark', surface: DARK_SURFACE });
  await expect(page.locator('input[name="theme-mode"][value="dark"]')).toBeChecked();
});

test('cached custom colours apply in light mode only and never move chess-side swatches', async ({ page }) => {
  const custom = { bg: '#123456' };
  await page.emulateMedia({ colorScheme: 'light' });
  await prepare(page, {}, custom);
  await page.goto('/settings');

  expect(await firstTheme(page)).toEqual({
    attr: null, surface: CUSTOM_SURFACE, pieceWhite: LIGHT_SURFACE,
  });

  await page.emulateMedia({ colorScheme: 'dark' });
  await expect.poll(() => readTheme(page)).toEqual({
    attr: null, surface: DARK_SURFACE, pieceWhite: 'rgb(201, 196, 184)',
  });
});
