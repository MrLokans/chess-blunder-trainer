import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { Button } from '../../src/components/Button';

describe('Button', () => {
  test('renders children', () => {
    render(<Button>Save</Button>);
    expect(screen.getByRole('button').textContent).toBe('Save');
  });

  test('default variant and size are primary/md', () => {
    render(<Button>X</Button>);
    const cls = screen.getByRole('button').className;
    expect(cls).toContain('btn--primary');
    expect(cls).toContain('btn--md');
  });

  test('applies variant class', () => {
    render(<Button variant="danger">X</Button>);
    expect(screen.getByRole('button').className).toContain('btn--danger');
  });

  test('applies size class', () => {
    render(<Button size="sm">X</Button>);
    expect(screen.getByRole('button').className).toContain('btn--sm');
  });

  test('forwards onClick when enabled', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button onClick={onClick}>X</Button>);
    await user.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  test('disabled blocks onClick', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button disabled onClick={onClick}>X</Button>);
    await user.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  test('loading state shows spinner and disables button', () => {
    render(<Button loading>Save</Button>);
    const btn = screen.getByRole('button');
    expect(btn.hasAttribute('disabled')).toBe(true);
    expect(btn.getAttribute('aria-busy')).toBe('true');
    expect(btn.querySelector('.btn__spinner')).not.toBeNull();
  });

  test('loading also blocks onClick', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Button loading onClick={onClick}>X</Button>);
    await user.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  test('type defaults to button (not submit)', () => {
    render(<Button>X</Button>);
    expect(screen.getByRole('button').getAttribute('type')).toBe('button');
  });

  test('type=submit is forwarded', () => {
    render(<Button type="submit">X</Button>);
    expect(screen.getByRole('button').getAttribute('type')).toBe('submit');
  });

  test('non-loading button has no aria-busy attribute', () => {
    render(<Button>X</Button>);
    expect(screen.getByRole('button').hasAttribute('aria-busy')).toBe(false);
  });
});
