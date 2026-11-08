import { Modal } from '../../components/feedback/Modal';

interface ShortcutsOverlayProps {
  visible: boolean;
  onClose: () => void;
}

export function ShortcutsOverlay({ visible, onClose }: ShortcutsOverlayProps): preact.JSX.Element {
  return (
    <Modal open={visible} onClose={onClose} title={t('trainer.shortcuts.title')} size="sm">
      <table class="shortcuts-table">
        <tbody>
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
    </Modal>
  );
}
