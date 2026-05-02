import { describe, test, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import userEvent from '@testing-library/user-event';
import { Card } from '../../src/components/Card';

describe('Card', () => {
  test('renders children inside a div by default', () => {
    const { container } = render(<Card>hello</Card>);
    const card = container.firstElementChild;
    expect(card?.tagName).toBe('DIV');
    expect(card?.textContent).toBe('hello');
  });

  test('renders as the requested element', () => {
    const { container } = render(<Card as="article">x</Card>);
    expect(container.firstElementChild?.tagName).toBe('ARTICLE');
  });

  test('non-interactive card has no role and no tabindex', () => {
    const { container } = render(<Card>x</Card>);
    const card = container.firstElementChild;
    expect(card?.hasAttribute('role')).toBe(false);
    expect(card?.hasAttribute('tabindex')).toBe(false);
    expect(card?.className).not.toContain('card-surface--interactive');
  });

  test('interactive card forwards onClick and is keyboard-reachable', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Card interactive onClick={onClick}>click me</Card>);

    const card = screen.getByRole('button');
    expect(card.getAttribute('tabindex')).toBe('0');
    expect(card.className).toContain('card-surface--interactive');

    await user.click(card);
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  test('interactive card activates on Enter and Space', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    render(<Card interactive onClick={onClick}>x</Card>);
    screen.getByRole('button').focus();
    await user.keyboard('{Enter}');
    expect(onClick).toHaveBeenCalledTimes(1);
    await user.keyboard(' ');
    expect(onClick).toHaveBeenCalledTimes(2);
  });

  test('non-interactive card ignores onClick prop (no listener attached)', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    const { container } = render(<Card onClick={onClick}>x</Card>);
    await user.click(container.firstElementChild as Element);
    expect(onClick).not.toHaveBeenCalled();
  });
});
