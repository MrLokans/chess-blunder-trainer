interface ShortcutsOverlayProps {
  visible: boolean;
  onClose: () => void;
}

export function ShortcutsOverlay({ visible, onClose }: ShortcutsOverlayProps): preact.JSX.Element | null {
  if (!visible) return null;

  const handleBackdropClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div class="shortcuts-overlay visible" id="shortcutsOverlay" onClick={handleBackdropClick}>
      <div class="shortcuts-modal">
        <div class="shortcuts-header">
          <h3>{t('trainer.shortcuts.title')}</h3>
          <button class="shortcuts-close" id="shortcutsClose" onClick={onClose}>&times;</button>
        </div>
        <table class="shortcuts-table">
          <tbody>
            <tr><td><kbd>Enter</kbd></td><td>{t('trainer.shortcuts.submit')}</td></tr>
            <tr><td><kbd>N</kbd></td><td>{t('trainer.shortcuts.next')}</td></tr>
            <tr><td><kbd>R</kbd></td><td>{t('trainer.shortcuts.reset')}</td></tr>
            <tr><td><kbd>B</kbd></td><td>{t('trainer.shortcuts.show_best')}</td></tr>
            <tr><td><kbd>P</kbd></td><td>{t('trainer.shortcuts.play_best')}</td></tr>
            <tr><td><kbd>F</kbd></td><td>{t('trainer.shortcuts.flip')}</td></tr>
            <tr><td><kbd>A</kbd></td><td>{t('trainer.shortcuts.arrows')}</td></tr>
            <tr><td><kbd>T</kbd></td><td>{t('trainer.shortcuts.threats')}</td></tr>
            <tr><td><kbd>L</kbd></td><td>{t('trainer.shortcuts.lichess')}</td></tr>
            <tr><td><kbd>⌘Z</kbd> / <kbd>Ctrl+Z</kbd></td><td>{t('trainer.shortcuts.undo')}</td></tr>
            <tr><td><kbd>:</kbd></td><td>{t('trainer.shortcuts.type_move')}</td></tr>
            <tr><td><kbd>?</kbd></td><td>{t('trainer.shortcuts.show_help')}</td></tr>
            <tr><td><kbd>Esc</kbd></td><td>{t('trainer.shortcuts.close_help')}</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
