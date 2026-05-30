import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/preact';
import { Segmented } from '../../src/components/Segmented';

const OPTS = [
  { label: '1', value: 1 },
  { label: '2', value: 2 },
  { label: '3', value: 3 },
];

describe('Segmented', () => {
  it('renders one button per option and marks the active one', () => {
    const { getByText } = render(
      <Segmented options={OPTS} value={2} onChange={() => {}} ariaLabel="Lines" />,
    );
    expect(getByText('1').className).not.toContain('segmented__btn--active');
    expect(getByText('2').className).toContain('segmented__btn--active');
  });

  it('calls onChange with the option value on click', () => {
    const onChange = vi.fn();
    const { getByText } = render(
      <Segmented options={OPTS} value={2} onChange={onChange} ariaLabel="Lines" />,
    );
    fireEvent.click(getByText('3'));
    expect(onChange).toHaveBeenCalledWith(3);
  });
});
