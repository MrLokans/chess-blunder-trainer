import { bus } from '../shared/event-bus';
import * as state from './state';
import * as ui from './ui';
import { navigateLine } from './line-player';
import { isVimInputActive } from './vim-input';

export function initKeyboard(): void {
  document.addEventListener('keydown', (e: KeyboardEvent) => {
    if (isVimInputActive()) return;
    const tag = ((e.target as HTMLElement)?.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') return;
    if (state.isAnimating()) return;

    if (e.key === 'Escape') {
      if (ui.isShortcutsOverlayVisible()) {
        ui.toggleShortcutsOverlay();
        return;
      }
      if (ui.isBoardResultVisible()) {
        ui.hideBoardResult();
      }
      return;
    }

    if (e.key === '?') { ui.toggleShortcutsOverlay(); return; }

    if (e.key === 'Enter' && !state.get('submitted')) {
      e.preventDefault();
      bus.emit('action:submit' as never);
    } else if (e.key === 'n' || e.key === 'N') {
      bus.emit('action:next' as never);
    } else if (e.key === 'r' || e.key === 'R') {
      bus.emit('action:reset' as never);
    } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      bus.emit('action:undo' as never);
    } else if (e.key === 'f' || e.key === 'F') {
      bus.emit('action:flip' as never);
    } else if (e.key === 'b' || e.key === 'B') {
      bus.emit('action:reveal' as never);
    } else if (e.key === 'p' || e.key === 'P') {
      bus.emit('action:playBest' as never);
    } else if (e.key === 'a' || e.key === 'A') {
      const el = document.getElementById('showArrows') as HTMLInputElement | null;
      if (el) {
        el.checked = !el.checked;
        el.dispatchEvent(new Event('change'));
      }
    } else if (e.key === 't' || e.key === 'T') {
      const el = document.getElementById('showThreats') as HTMLInputElement | null;
      if (el) {
        el.checked = !el.checked;
        el.dispatchEvent(new Event('change'));
      }
    } else if (e.key === 'l' || e.key === 'L') {
      bus.emit('action:lichess' as never);
    } else if (e.key === 'ArrowLeft') {
      navigateLine(-1);
    } else if (e.key === 'ArrowRight') {
      navigateLine(1);
    } else if (e.key === ':') {
      e.preventDefault();
      bus.emit('action:vimInput' as never);
    }
  });
}
