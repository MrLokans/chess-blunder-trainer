import { describe, test, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ConfirmDialog } from '../../src/components/ConfirmDialog';

afterEach(() => {
  cleanup();
  document.body.style.overflow = '';
});

const baseProps = {
  open: true,
  title: 'Delete?',
  message: 'This cannot be undone.',
  confirmLabel: 'Delete',
  cancelLabel: 'Cancel',
};

describe('ConfirmDialog', () => {
  test('renders title, message, confirm, and cancel', () => {
    render(<ConfirmDialog {...baseProps} onClose={() => {}} onConfirm={() => {}} />);
    expect(screen.getByText('Delete?')).toBeDefined();
    expect(screen.getByText('This cannot be undone.')).toBeDefined();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeDefined();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDefined();
  });

  test('confirm button calls onConfirm and onClose', async () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<ConfirmDialog {...baseProps} onClose={onClose} onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Delete' }));
    expect(onConfirm).toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  test('cancel button calls onClose only', async () => {
    const onConfirm = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<ConfirmDialog {...baseProps} onClose={onClose} onConfirm={onConfirm} />);
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onClose).toHaveBeenCalled();
    expect(onConfirm).not.toHaveBeenCalled();
  });

  test('destructive variant uses danger button class', () => {
    render(
      <ConfirmDialog
        {...baseProps}
        destructive
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(screen.getByRole('button', { name: 'Delete' }).className).toContain('btn--danger');
  });

  test('secondaryAction renders a third button + fires its handler', async () => {
    const primary = vi.fn();
    const secondary = vi.fn();
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(
      <ConfirmDialog
        {...baseProps}
        confirmLabel="Detach"
        onClose={onClose}
        onConfirm={primary}
        secondaryAction={{ label: 'Delete games too', destructive: true, onConfirm: secondary }}
      />,
    );
    expect(screen.getAllByRole('button')).toHaveLength(4); // cancel + secondary + confirm + modal close (×)
    await user.click(screen.getByRole('button', { name: 'Delete games too' }));
    expect(secondary).toHaveBeenCalled();
    expect(primary).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  test('defaultFocus=confirm focuses the primary action on open', () => {
    render(
      <ConfirmDialog
        {...baseProps}
        defaultFocus="confirm"
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(document.activeElement?.textContent).toBe('Delete');
  });

  test('defaultFocus=cancel focuses the cancel button on open', () => {
    render(
      <ConfirmDialog
        {...baseProps}
        defaultFocus="cancel"
        onClose={() => {}}
        onConfirm={() => {}}
      />,
    );
    expect(document.activeElement?.textContent).toBe('Cancel');
  });

  test('defaultFocus=secondary focuses the secondary action when present', () => {
    render(
      <ConfirmDialog
        {...baseProps}
        defaultFocus="secondary"
        onClose={() => {}}
        onConfirm={() => {}}
        secondaryAction={{ label: 'Detach', onConfirm: () => {} }}
      />,
    );
    expect(document.activeElement?.textContent).toBe('Detach');
  });
});
