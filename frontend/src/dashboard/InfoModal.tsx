import { useEffect, useCallback } from 'preact/hooks';
import type { ComponentChildren } from 'preact';

interface InfoModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ComponentChildren;
}

export function InfoModal({ open, onClose, title, children }: InfoModalProps) {
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (!open) return;
    document.addEventListener('keydown', handleKeyDown);
    return () => { document.removeEventListener('keydown', handleKeyDown); };
  }, [open, handleKeyDown]);

  if (!open) return null;

  return (
    <div
      class="info-modal-overlay visible"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div class="info-modal">
        <div class="info-modal-header">
          <h3>{title}</h3>
          <button class="info-modal-close" onClick={onClose}>&times;</button>
        </div>
        <div class="info-modal-body">
          {children}
        </div>
      </div>
    </div>
  );
}
