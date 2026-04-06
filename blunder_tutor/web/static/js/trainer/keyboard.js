import { bus } from '../event-bus.js';
import * as state from './state.js';
import * as ui from './ui.js';
import { navigateLine } from './line-player.js';
import { isVimInputActive } from './vim-input.js';

export function initKeyboard() {
  document.addEventListener('keydown', (e) => {
    if (isVimInputActive()) return;
    const tag = (e.target.tagName || '').toLowerCase();
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
      bus.emit('action:submit');
    } else if (e.key === 'n' || e.key === 'N') {
      bus.emit('action:next');
    } else if (e.key === 'r' || e.key === 'R') {
      bus.emit('action:reset');
    } else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      bus.emit('action:undo');
    } else if (e.key === 'f' || e.key === 'F') {
      bus.emit('action:flip');
    } else if (e.key === 'b' || e.key === 'B') {
      bus.emit('action:reveal');
    } else if (e.key === 'p' || e.key === 'P') {
      bus.emit('action:playBest');
    } else if (e.key === 'a' || e.key === 'A') {
      const el = document.getElementById('showArrows');
      if (el) {
        el.checked = !el.checked;
        el.dispatchEvent(new Event('change'));
      }
    } else if (e.key === 't' || e.key === 'T') {
      const el = document.getElementById('showThreats');
      if (el) {
        el.checked = !el.checked;
        el.dispatchEvent(new Event('change'));
      }
    } else if (e.key === 'l' || e.key === 'L') {
      bus.emit('action:lichess');
    } else if (e.key === 'ArrowLeft') {
      navigateLine(-1);
    } else if (e.key === 'ArrowRight') {
      navigateLine(1);
    } else if (e.key === ':') {
      e.preventDefault();
      bus.emit('action:vimInput');
    }
  });
}
