import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { InfoModal } from '../../src/dashboard/InfoModal';

describe('InfoModal', () => {
  test('renders nothing when closed', () => {
    const { container } = render(<InfoModal open={false} onClose={() => {}} title="Help">Content</InfoModal>);
    expect(container.innerHTML).toBe('');
  });

  test('renders content when open', () => {
    render(<InfoModal open={true} onClose={() => {}} title="Help">Modal body</InfoModal>);
    expect(screen.getByText('Help')).toBeDefined();
    expect(screen.getByText('Modal body')).toBeDefined();
  });

  test('calls onClose when close button clicked', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<InfoModal open={true} onClose={onClose} title="Help">Content</InfoModal>);
    await user.click(screen.getByText('\u00d7'));
    expect(onClose).toHaveBeenCalled();
  });

  test('calls onClose on Escape key', async () => {
    const onClose = vi.fn();
    const user = userEvent.setup();
    render(<InfoModal open={true} onClose={onClose} title="Help">Content</InfoModal>);
    await user.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalled();
  });
});
