import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { RangeSlider } from '../../src/components/RangeSlider';

describe('RangeSlider', () => {
  it('renders an input[type=range] with min/max/value', () => {
    const { container } = render(
      <RangeSlider min={5} max={30} value={20} onChange={() => {}} ariaLabel="Max depth" />,
    );
    const input = container.querySelector('input[type="range"]') as HTMLInputElement;
    expect(input).not.toBeNull();
    expect(input.min).toBe('5');
    expect(input.max).toBe('30');
    expect(input.value).toBe('20');
    expect(input.getAttribute('aria-label')).toBe('Max depth');
  });

  it('calls onChange with the numeric value on input', () => {
    const onChange = vi.fn();
    const { container } = render(
      <RangeSlider min={5} max={30} value={20} onChange={onChange} ariaLabel="Max depth" />,
    );
    const input = container.querySelector('input[type="range"]') as HTMLInputElement;
    input.value = '12';
    fireEvent.input(input);
    expect(onChange).toHaveBeenCalledWith(12);
  });
});
