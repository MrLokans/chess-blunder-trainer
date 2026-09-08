import { describe, test, expect, beforeEach, afterEach } from 'vitest';
import { applyBoardTheme, readBoardColors } from '../../src/shared/board-theme';

function inlineBoardColors(): { light: string; dark: string } {
  const root = document.documentElement;
  return {
    light: root.style.getPropertyValue('--board-light'),
    dark: root.style.getPropertyValue('--board-dark'),
  };
}

function setTokenDefault(light: string, dark: string): void {
  let sheet = document.getElementById('token-default') as HTMLStyleElement | null;
  if (!sheet) {
    sheet = document.createElement('style');
    sheet.id = 'token-default';
    document.head.appendChild(sheet);
  }
  sheet.textContent = `:root { --board-light: ${light}; --board-dark: ${dark}; }`;
}

describe('board theme', () => {
  beforeEach(() => {
    setTokenDefault('#A9A297', '#6E675C');
  });

  afterEach(() => {
    document.getElementById('token-default')?.remove();
    document.getElementById('cg-board-bg')?.remove();
    document.documentElement.style.removeProperty('--board-light');
    document.documentElement.style.removeProperty('--board-dark');
  });

  describe('applyBoardTheme', () => {
    test('explicit colours are pinned as inline custom properties', () => {
      applyBoardTheme('#f0d9b5', '#b58863');
      expect(inlineBoardColors()).toEqual({ light: '#f0d9b5', dark: '#b58863' });
    });

    test('null clears the inline overrides so the mode-aware token wins', () => {
      applyBoardTheme('#f0d9b5', '#b58863');
      applyBoardTheme(null, null);
      expect(inlineBoardColors()).toEqual({ light: '', dark: '' });
      expect(readBoardColors()).toEqual({ light: '#A9A297', dark: '#6E675C' });
    });

    test('a half-set pair is treated as unset rather than painting a mismatched board', () => {
      applyBoardTheme('#f0d9b5', null);
      expect(inlineBoardColors()).toEqual({ light: '', dark: '' });
    });

    test('clears a leftover SVG paint stylesheet', () => {
      const leftover = document.createElement('style');
      leftover.id = 'cg-board-bg';
      document.head.appendChild(leftover);
      applyBoardTheme(null, null);
      expect(document.getElementById('cg-board-bg')).toBeNull();
    });
  });

  describe('readBoardColors', () => {
    test('an explicit inline override beats the token default', () => {
      document.documentElement.style.setProperty('--board-light', '#111111');
      document.documentElement.style.setProperty('--board-dark', '#222222');
      expect(readBoardColors()).toEqual({ light: '#111111', dark: '#222222' });
    });
  });
});
