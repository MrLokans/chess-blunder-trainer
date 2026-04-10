import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { ColorInput } from '../../src/components/ColorInput';

describe('ColorInput', () => {
  test('renders color picker and hex input with initial value', () => {
    render(<ColorInput value="#FF0000" onChange={() => {}} />);
    const colorInput = screen.getByLabelText('color picker');
    const hexInput = screen.getByLabelText('hex value');

    expect(colorInput.value).toBe('#ff0000');
    expect(hexInput.value).toBe('#FF0000');
  });

  test('calls onChange when hex input receives valid color', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ColorInput value="#FF0000" onChange={onChange} />);

    const hexInput = screen.getByLabelText('hex value');
    await user.clear(hexInput);
    await user.type(hexInput, '#00FF00');
    expect(onChange).toHaveBeenLastCalledWith('#00FF00');
  });

  test('does not call onChange for invalid hex input', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<ColorInput value="#FF0000" onChange={onChange} />);

    const hexInput = screen.getByLabelText('hex value');
    await user.clear(hexInput);
    await user.type(hexInput, 'xyz');
    expect(onChange).not.toHaveBeenCalled();
  });

  test('normalizes hex display to uppercase', () => {
    render(<ColorInput value="#aabbcc" onChange={() => {}} />);
    const hexInput = screen.getByLabelText('hex value');
    expect(hexInput.value).toBe('#AABBCC');
  });
});
