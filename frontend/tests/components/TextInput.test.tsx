import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { TextInput } from '../../src/components/TextInput';

describe('TextInput', () => {
  test('renders with current value', () => {
    render(<TextInput value="hello" onChange={() => {}} />);
    const input = screen.getByRole('textbox');
    expect((input as HTMLInputElement).value).toBe('hello');
  });

  test('onChange receives a string, not an event', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TextInput value="" onChange={onChange} />);
    await user.type(screen.getByRole('textbox'), 'a');
    expect(onChange).toHaveBeenCalledWith('a');
    expect(onChange.mock.calls[0]?.[0]).toBe('a');
  });

  test('disabled blocks user input', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<TextInput value="" onChange={onChange} disabled />);
    await user.type(screen.getByRole('textbox'), 'a');
    expect(onChange).not.toHaveBeenCalled();
  });

  test('type=email uses email input', () => {
    render(<TextInput value="" onChange={() => {}} type="email" />);
    const input = document.querySelector('input[type="email"]');
    expect(input).not.toBeNull();
  });

  test('type=password uses password input', () => {
    const { container } = render(<TextInput value="" onChange={() => {}} type="password" />);
    expect(container.querySelector('input[type="password"]')).not.toBeNull();
  });

  test('invalid sets aria-invalid and modifier class', () => {
    render(<TextInput value="" onChange={() => {}} invalid />);
    const input = screen.getByRole('textbox');
    expect(input.getAttribute('aria-invalid')).toBe('true');
    expect(input.className).toContain('text-input--invalid');
  });

  test('placeholder is forwarded', () => {
    render(<TextInput value="" onChange={() => {}} placeholder="Type here" />);
    const input = screen.getByRole('textbox');
    expect((input as HTMLInputElement).placeholder).toBe('Type here');
  });
});
