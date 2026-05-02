import { describe, test, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { useRef } from 'preact/hooks';
import { Modal } from '../../src/components/Modal';

describe('Modal', () => {
  beforeEach(() => {
    document.body.style.overflow = '';
  });

  afterEach(() => {
    cleanup();
    document.body.style.overflow = '';
  });

  test('renders nothing when closed', () => {
    render(
      <Modal open={false} onClose={() => {}} title="Hi">
        body
      </Modal>,
    );
    expect(screen.queryByRole('dialog')).toBeNull();
  });

  test('renders dialog with aria-labelledby pointing at the title', () => {
    render(
      <Modal open={true} onClose={() => {}} title="Add profile">
        body
      </Modal>,
    );
    const dialog = screen.getByRole('dialog');
    const labelledBy = dialog.getAttribute('aria-labelledby');
    if (!labelledBy) throw new Error('aria-labelledby missing');
    expect(document.getElementById(labelledBy)?.textContent).toBe('Add profile');
  });

  test('Escape key calls onClose', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<Modal open={true} onClose={onClose} title="X">x</Modal>);
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });

  test('Escape does NOT stopPropagation (allows nested handlers)', async () => {
    const outer = vi.fn();
    document.addEventListener('keydown', outer);
    const user = userEvent.setup();
    render(<Modal open={true} onClose={() => {}} title="X">x</Modal>);
    await user.keyboard('{Escape}');
    expect(outer).toHaveBeenCalled();
    document.removeEventListener('keydown', outer);
  });

  test('clicking the backdrop closes', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<Modal open={true} onClose={onClose} title="X">x</Modal>);
    const backdrop = document.querySelector('.modal-overlay');
    if (!backdrop) throw new Error('backdrop missing');
    await user.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  test('clicking inside the dialog body does NOT close', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<Modal open={true} onClose={onClose} title="X">x</Modal>);
    await user.click(screen.getByRole('dialog'));
    expect(onClose).not.toHaveBeenCalled();
  });

  test('close button calls onClose and uses default Close label', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<Modal open={true} onClose={onClose} title="X">x</Modal>);
    await user.click(screen.getByRole('button', { name: 'Close' }));
    expect(onClose).toHaveBeenCalled();
  });

  test('closeLabel prop overrides the close-button aria-label', () => {
    render(
      <Modal open={true} onClose={() => {}} title="X" closeLabel="Cerrar">x</Modal>,
    );
    expect(screen.getByRole('button', { name: 'Cerrar' })).toBeDefined();
  });

  test('locks body scroll while open and restores on unmount', () => {
    document.body.style.overflow = 'auto';
    const { unmount } = render(<Modal open={true} onClose={() => {}} title="X">x</Modal>);
    expect(document.body.style.overflow).toBe('hidden');
    unmount();
    expect(document.body.style.overflow).toBe('auto');
  });

  test('default focus targets the dialog container (safer for destructive flows)', () => {
    render(
      <Modal open={true} onClose={() => {}} title="X">
        <button type="button">First</button>
        <button type="button">Second</button>
      </Modal>,
    );
    expect(document.activeElement).toBe(screen.getByRole('dialog'));
  });

  test('initialFocusRef opts in to a specific initial focus target', () => {
    function Harness() {
      const ref = useRef<HTMLButtonElement>(null);
      return (
        <Modal open={true} onClose={() => {}} title="X" initialFocusRef={ref}>
          <button type="button">First</button>
          <button type="button" ref={ref}>Second</button>
        </Modal>
      );
    }
    render(<Harness />);
    expect(document.activeElement?.textContent).toBe('Second');
  });

  test('restores focus to the previously focused element on close', () => {
    const trigger = document.createElement('button');
    trigger.textContent = 'opener';
    document.body.appendChild(trigger);
    trigger.focus();
    expect(document.activeElement).toBe(trigger);

    const { unmount } = render(<Modal open={true} onClose={() => {}} title="X">x</Modal>);
    unmount();
    expect(document.activeElement).toBe(trigger);
    document.body.removeChild(trigger);
  });
});
