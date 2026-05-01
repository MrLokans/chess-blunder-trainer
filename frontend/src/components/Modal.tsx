import type { ComponentChildren, RefObject } from 'preact';
import { createPortal } from 'preact/compat';
import { useEffect, useId, useRef } from 'preact/hooks';

export type ModalSize = 'sm' | 'md' | 'lg';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  size?: ModalSize;
  initialFocusRef?: RefObject<HTMLElement>;
  closeLabel?: string;
  children?: ComponentChildren;
}

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

export function Modal({
  open,
  onClose,
  title,
  size = 'md',
  initialFocusRef,
  closeLabel = 'Close',
  children,
}: ModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const previouslyFocusedRef = useRef<HTMLElement | null>(null);
  const titleId = useId();

  useEffect(() => {
    if (!open) return;

    previouslyFocusedRef.current = document.activeElement as HTMLElement | null;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const node = dialogRef.current;
    if (node) {
      const explicit = initialFocusRef?.current;
      const target = explicit ?? node;
      target.focus();
    }

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key !== 'Tab' || !node) return;

      const focusables = Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
      const firstEl = focusables[0];
      const lastEl = focusables[focusables.length - 1];
      if (!firstEl || !lastEl) return;
      const active = document.activeElement;

      if (e.shiftKey && active === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && active === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocusedRef.current?.focus();
    };
  }, [open, onClose, initialFocusRef]);

  if (!open) return null;

  const handleBackdropClick = (e: MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return createPortal(
    <div class="modal-overlay visible" onClick={handleBackdropClick}>
      <div
        ref={dialogRef}
        class={`modal modal--${size}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
      >
        <div class="modal-header">
          <h3 id={titleId}>{title}</h3>
          <button type="button" class="modal-close" onClick={onClose} aria-label={closeLabel}>
            &times;
          </button>
        </div>
        <div ref={bodyRef} class="modal__body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
