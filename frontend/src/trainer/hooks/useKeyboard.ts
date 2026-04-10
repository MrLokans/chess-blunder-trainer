import { useEffect } from 'preact/hooks';

interface KeyboardActions {
  submit: () => void;
  next: () => void;
  reset: () => void;
  undo: () => void;
  flip: () => void;
  reveal: () => void;
  playBest: () => void;
  lichess: () => void;
  vimInput: () => void;
  toggleShortcuts: () => void;
  navigateLine: (direction: 'forward' | 'back') => void;
  toggleArrows: () => void;
  toggleThreats: () => void;
  isAnimating: boolean;
  isVimInputActive: boolean;
  isShortcutsVisible: boolean;
  isResultVisible: boolean;
  hideResult: () => void;
}

export function useKeyboard(actions: KeyboardActions): void {
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent): void {
      if (actions.isVimInputActive) return;

      const target = e.target as HTMLElement;
      const tag = target.tagName.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      if (actions.isAnimating) return;

      if (e.key === 'Escape') {
        if (actions.isShortcutsVisible) {
          actions.toggleShortcuts();
        } else if (actions.isResultVisible) {
          actions.hideResult();
        }
        return;
      }

      if (e.key === '?') {
        e.preventDefault();
        actions.toggleShortcuts();
        return;
      }

      if (e.key === 'Enter') {
        e.preventDefault();
        actions.submit();
        return;
      }

      if ((e.ctrlKey || e.metaKey) && e.key === 'z') {
        e.preventDefault();
        actions.undo();
        return;
      }

      const key = e.key.toLowerCase();

      if (key === 'n') { actions.next(); return; }
      if (key === 'r') { actions.reset(); return; }
      if (key === 'f') { actions.flip(); return; }
      if (key === 'b') { actions.reveal(); return; }
      if (key === 'p') { actions.playBest(); return; }
      if (key === 'a') { actions.toggleArrows(); return; }
      if (key === 't') { actions.toggleThreats(); return; }
      if (key === 'l') { actions.lichess(); return; }

      if (e.key === 'ArrowLeft') { actions.navigateLine('back'); return; }
      if (e.key === 'ArrowRight') { actions.navigateLine('forward'); return; }

      if (e.key === ':') {
        e.preventDefault();
        actions.vimInput();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [actions]);
}
