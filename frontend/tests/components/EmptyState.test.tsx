import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { EmptyState } from '../../src/components/EmptyState';

describe('EmptyState', () => {
  test('renders title and message', () => {
    render(<EmptyState title="Nothing here" message="Add your first item" />);
    expect(screen.getByText('Nothing here')).toBeDefined();
    expect(screen.getByText('Add your first item')).toBeDefined();
  });

  test('renders icon when provided', () => {
    const { container } = render(
      <EmptyState icon="📭" title="X" message="Y" />,
    );
    expect(container.querySelector('.empty-state-icon')?.textContent).toBe('📭');
  });

  test('omits icon container when no icon provided', () => {
    const { container } = render(<EmptyState title="X" message="Y" />);
    expect(container.querySelector('.empty-state-icon')).toBeNull();
  });

  test('renders action when provided', () => {
    render(
      <EmptyState
        title="X"
        message="Y"
        action={<button type="button">Do it</button>}
      />,
    );
    expect(screen.getByRole('button', { name: 'Do it' })).toBeDefined();
  });

  test('omits action container when no action provided', () => {
    const { container } = render(<EmptyState title="X" message="Y" />);
    expect(container.querySelector('.empty-state-actions')).toBeNull();
  });
});
