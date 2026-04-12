import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { Alert } from '../../src/components/Alert';

describe('Alert', () => {
  test('renders nothing when message is null', () => {
    const { container } = render(<Alert type="error" message={null} />);
    expect(container.innerHTML).toBe('');
  });

  test('renders nothing when message is empty string', () => {
    const { container } = render(<Alert type="error" message="" />);
    expect(container.innerHTML).toBe('');
  });

  test('renders error alert with message', () => {
    render(<Alert type="error" message="Something went wrong" />);
    const alert = screen.getByRole('alert');
    expect(alert).toBeDefined();
    expect(alert.textContent).toBe('Something went wrong');
    expect(alert.className).toContain('alert-error');
  });

  test('renders success alert with message', () => {
    render(<Alert type="success" message="Saved!" />);
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe('Saved!');
    expect(alert.className).toContain('alert-success');
  });

  test('updates when message changes', () => {
    const { rerender } = render(<Alert type="error" message="First" />);
    expect(screen.getByRole('alert').textContent).toBe('First');

    rerender(<Alert type="error" message="Second" />);
    expect(screen.getByRole('alert').textContent).toBe('Second');
  });

  test('disappears when message becomes null', () => {
    const { container, rerender } = render(<Alert type="error" message="Visible" />);
    expect(screen.getByRole('alert')).toBeDefined();

    rerender(<Alert type="error" message={null} />);
    expect(container.innerHTML).toBe('');
  });
});
