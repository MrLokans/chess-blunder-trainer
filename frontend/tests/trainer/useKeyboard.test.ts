import { describe, expect, it, vi } from 'vitest';
import { renderHook } from '@testing-library/preact';
import { fireEvent } from '@testing-library/preact';
import { useKeyboard } from '../../src/trainer/hooks/useKeyboard';

function actions(overrides: Partial<Parameters<typeof useKeyboard>[0]> = {}): Parameters<typeof useKeyboard>[0] {
  return {
    next: vi.fn(), reset: vi.fn(), undo: vi.fn(), flip: vi.fn(), reveal: vi.fn(), playBest: vi.fn(),
    lichess: vi.fn(), vimInput: vi.fn(), toggleShortcuts: vi.fn(), navigateLine: vi.fn(),
    toggleArrows: vi.fn(), toggleThreats: vi.fn(), hideResult: vi.fn(),
    isAnimating: false, isVimInputActive: false, isShortcutsVisible: false, isResultVisible: false,
    ...overrides,
  };
}

describe('useKeyboard', () => {
  it('leaves arrow keys on a focused radio to the radio group', () => {
    const handlers = actions();
    renderHook(() => { useKeyboard(handlers); });
    const radio = document.createElement('input');
    radio.type = 'radio';
    document.body.appendChild(radio);

    fireEvent.keyDown(radio, { key: 'ArrowRight' });
    expect(handlers.navigateLine).not.toHaveBeenCalled();

    fireEvent.keyDown(document.body, { key: 'ArrowRight' });
    expect(handlers.navigateLine).toHaveBeenCalledWith('forward');
    radio.remove();
  });

  it('ignores puzzle shortcuts and Escape while the shortcuts dialog is open', () => {
    const handlers = actions({ isShortcutsVisible: true, isResultVisible: true });
    renderHook(() => { useKeyboard(handlers); });

    fireEvent.keyDown(document.body, { key: 'n' });
    fireEvent.keyDown(document.body, { key: 'Escape' });
    expect(handlers.next).not.toHaveBeenCalled();
    expect(handlers.hideResult).not.toHaveBeenCalled();
    expect(handlers.toggleShortcuts).not.toHaveBeenCalled();

    fireEvent.keyDown(document.body, { key: '?' });
    expect(handlers.toggleShortcuts).toHaveBeenCalledOnce();
  });
});
