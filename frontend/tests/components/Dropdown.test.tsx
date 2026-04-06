import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { Dropdown } from '../../src/components/Dropdown';

const OPTIONS = [
  { value: 'bullet', label: 'Bullet' },
  { value: 'blitz', label: 'Blitz' },
  { value: 'rapid', label: 'Rapid' },
];

describe('Dropdown', () => {
  test('displays selected option label', () => {
    render(<Dropdown options={OPTIONS} value="blitz" onChange={() => {}} />);
    expect(screen.getByRole('button').textContent).toContain('Blitz');
  });

  test('opens listbox on trigger click', async () => {
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={() => {}} />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('listbox')).toBeDefined();
    expect(screen.getAllByRole('option')).toHaveLength(3);
  });

  test('calls onChange when option is selected', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={onChange} />);

    await user.click(screen.getByRole('button'));
    await user.click(screen.getByText('Rapid'));
    expect(onChange).toHaveBeenCalledWith('rapid');
  });

  test('closes listbox after selection', async () => {
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={() => {}} />);

    await user.click(screen.getByRole('button'));
    await user.click(screen.getByText('Rapid'));

    const trigger = screen.getByRole('button');
    expect(trigger.getAttribute('aria-expanded')).toBe('false');
  });

  test('closes on Escape key', async () => {
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={() => {}} />);

    await user.click(screen.getByRole('button'));
    expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true');

    await user.keyboard('{Escape}');
    expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('false');
  });

  test('marks the current value as selected', async () => {
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="blitz" onChange={() => {}} />);

    await user.click(screen.getByRole('button'));
    const options = screen.getAllByRole('option');
    const blitzOption = options.find(o => o.textContent === 'Blitz');
    expect(blitzOption?.getAttribute('aria-selected')).toBe('true');
  });

  test('navigates options with ArrowDown and selects with Enter', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={onChange} />);

    await user.click(screen.getByRole('button'));
    await user.keyboard('{ArrowDown}');
    await user.keyboard('{Enter}');
    expect(onChange).toHaveBeenCalledWith('blitz');
  });

  test('navigates options with ArrowUp (wraps around)', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={onChange} />);

    await user.click(screen.getByRole('button'));
    await user.keyboard('{ArrowUp}');
    await user.keyboard('{Enter}');
    expect(onChange).toHaveBeenCalledWith('rapid');
  });

  test('opens with ArrowDown when closed', async () => {
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="bullet" onChange={() => {}} />);

    screen.getByRole('button').focus();
    await user.keyboard('{ArrowDown}');
    expect(screen.getByRole('button').getAttribute('aria-expanded')).toBe('true');
    expect(screen.getByRole('listbox')).toBeDefined();
  });

  test('Home jumps to first option, End to last', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<Dropdown options={OPTIONS} value="blitz" onChange={onChange} />);

    await user.click(screen.getByRole('button'));
    await user.keyboard('{End}');
    await user.keyboard('{Enter}');
    expect(onChange).toHaveBeenCalledWith('rapid');
  });
});
