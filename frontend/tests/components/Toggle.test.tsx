import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { Toggle } from '../../src/components/Toggle';

describe('Toggle', () => {
  test('renders as a switch with the right aria-checked', () => {
    render(<Toggle value={true} onChange={() => {}} />);
    const sw = screen.getByRole('switch');
    expect(sw.getAttribute('aria-checked')).toBe('true');
  });

  test('clicking off → on calls onChange(true)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Toggle value={false} onChange={onChange} />);
    await user.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith(true);
  });

  test('clicking on → off calls onChange(false)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Toggle value={true} onChange={onChange} />);
    await user.click(screen.getByRole('switch'));
    expect(onChange).toHaveBeenCalledWith(false);
  });

  test('disabled blocks click and propagates to button', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Toggle value={false} onChange={onChange} disabled />);
    const sw = screen.getByRole('switch');
    expect(sw.hasAttribute('disabled')).toBe(true);
    await user.click(sw);
    expect(onChange).not.toHaveBeenCalled();
  });

  test('inline label renders alongside the switch', () => {
    render(<Toggle value={false} onChange={() => {}} label="Auto-sync" />);
    expect(screen.getByText('Auto-sync')).toBeDefined();
  });

  test('on state adds the on modifier class to the track', () => {
    render(<Toggle value={true} onChange={() => {}} />);
    expect(screen.getByRole('switch').className).toContain('toggle__track--on');
  });
});
