import { useRef } from 'preact/hooks';
import { Modal } from './Modal';
import { Button } from './Button';

export interface ConfirmDialogAction {
  label: string;
  destructive?: boolean;
  onConfirm: () => void;
}

export type ConfirmDefaultFocus = 'confirm' | 'cancel' | 'secondary';

export interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  message: string;
  confirmLabel: string;
  cancelLabel: string;
  destructive?: boolean;
  defaultFocus?: ConfirmDefaultFocus;
  onConfirm: () => void;
  secondaryAction?: ConfirmDialogAction;
}

export function ConfirmDialog({
  open,
  onClose,
  title,
  message,
  confirmLabel,
  cancelLabel,
  destructive = false,
  defaultFocus = 'confirm',
  onConfirm,
  secondaryAction,
}: ConfirmDialogProps) {
  const confirmRef = useRef<HTMLButtonElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  const secondaryRef = useRef<HTMLButtonElement>(null);

  const initialFocusRef =
    defaultFocus === 'cancel'
      ? cancelRef
      : defaultFocus === 'secondary'
        ? secondaryRef
        : confirmRef;

  const handleConfirm = () => {
    onConfirm();
    onClose();
  };

  const handleSecondary = () => {
    if (secondaryAction) {
      secondaryAction.onConfirm();
      onClose();
    }
  };

  return (
    <Modal open={open} onClose={onClose} title={title} size="sm" initialFocusRef={initialFocusRef}>
      <p class="confirm-dialog__message">{message}</p>
      <div class="confirm-dialog__actions">
        <Button ref={cancelRef} variant="ghost" onClick={onClose}>
          {cancelLabel}
        </Button>
        {secondaryAction && (
          <Button
            ref={secondaryRef}
            variant={secondaryAction.destructive ? 'danger' : 'secondary'}
            onClick={handleSecondary}
          >
            {secondaryAction.label}
          </Button>
        )}
        <Button
          ref={confirmRef}
          variant={destructive ? 'danger' : 'primary'}
          onClick={handleConfirm}
        >
          {confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}
