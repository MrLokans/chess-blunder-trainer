import { test, expect } from '@playwright/test';

const TOKENS = [
  '--surface', '--surface-raised', '--surface-overlay', '--surface-sunken', '--surface-hover', '--surface-inverse',
  '--text', '--text-secondary', '--text-muted', '--text-disabled', '--text-inverse', '--text-on-accent',
  '--border', '--border-subtle', '--border-card', '--border-strong', '--border-control', '--border-hover', '--border-swatch',
  '--control-accent', '--accent', '--accent-hover', '--success', '--success-hover', '--warning-hover',
  '--error', '--error-hover', '--info', '--success-bg', '--success-border', '--warning-bg', '--error-bg',
  '--error-border', '--info-bg', '--info-border', '--bg-phase', '--focus-ring-color', '--focus-ring-error',
  '--modal-backdrop', '--elevation-shadow', '--shadow-card', '--eval-white-advantage-fill', '--eval-black-fill',
  '--eval-black-advantage-fill', '--color-phase-opening', '--color-phase-endgame', '--heatmap-empty-future',
  '--heatmap-empty', '--heatmap-l1', '--heatmap-l2', '--heatmap-l3', '--heatmap-l4',
];

test.use({ colorScheme: 'dark' });

test('dark tokens match explicit and system theme activation', async ({ page }) => {
  await page.route('**/api/settings/theme', route => {
    return route.fulfill({
      json: { primary: '#123456', bg: '#123456', bg_card: '#123456' },
    });
  });
  await page.addInitScript(() => {
    localStorage.clear();
  });
  await page.goto('/settings');

  const palette = () => page.evaluate(tokens => {
    const style = getComputedStyle(document.documentElement);
    return Object.fromEntries(tokens.map(token => {
      return [token, style.getPropertyValue(token).trim()];
    }));
  }, TOKENS);
  const colors = () => page.evaluate(tokens => {
    const probe = document.createElement('div');
    document.body.append(probe);
    const values = Object.fromEntries(tokens.map(token => {
      probe.style.color = `var(${token})`;
      return [token, getComputedStyle(probe).color];
    }));
    probe.remove();
    return values;
  }, ['--surface', '--surface-raised', '--accent', '--success', '--error', '--eval-black-fill', '--heatmap-empty-future']);

  const system = await palette();
  const systemColors = await colors();
  expect(systemColors).toEqual({
    '--surface': 'rgb(22, 21, 15)',
    '--surface-raised': 'rgb(38, 36, 27)',
    '--accent': 'rgb(138, 161, 224)',
    '--success': 'rgb(79, 176, 95)',
    '--error': 'rgb(227, 133, 133)',
    '--eval-black-fill': 'rgb(58, 54, 43)',
    '--heatmap-empty-future': 'rgb(33, 31, 24)',
  });
  await page.evaluate(() => { document.documentElement.dataset.theme = 'dark'; });
  expect(await palette()).toEqual(system);
  expect(await colors()).toEqual(systemColors);
});
