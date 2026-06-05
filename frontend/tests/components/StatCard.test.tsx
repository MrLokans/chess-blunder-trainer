import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { StatCard } from '../../src/components/data/StatCard';

describe('StatCard', () => {
  test('renders label and value', () => {
    render(<StatCard label="Total Games" value={150} />);
    expect(screen.getByText('Total Games')).toBeDefined();
    expect(screen.getByText('150')).toBeDefined();
  });

  test('renders string value verbatim', () => {
    render(<StatCard label="Progress" value="50%" />);
    expect(screen.getByText('50%')).toBeDefined();
  });

  test('does not render delta or hint when omitted', () => {
    const { container } = render(<StatCard label="X" value={1} />);
    expect(container.querySelector('.stat-delta')).toBeNull();
    expect(container.querySelector('.stat-hint')).toBeNull();
  });

  test('renders delta with direction modifier class', () => {
    const { container } = render(
      <StatCard label="Rating" value={1400} delta={{ value: '+12', direction: 'up' }} />,
    );
    const delta = container.querySelector('.stat-delta');
    expect(delta).not.toBeNull();
    expect(delta?.className).toContain('stat-delta--up');
    expect(delta?.textContent).toContain('+12');
  });

  test('renders down and flat delta directions', () => {
    const { container: down } = render(
      <StatCard label="R" value={1} delta={{ value: '-3', direction: 'down' }} />,
    );
    expect(down.querySelector('.stat-delta')?.className).toContain('stat-delta--down');

    const { container: flat } = render(
      <StatCard label="R" value={1} delta={{ value: '0', direction: 'flat' }} />,
    );
    expect(flat.querySelector('.stat-delta')?.className).toContain('stat-delta--flat');
  });

  test('renders hint when provided', () => {
    render(<StatCard label="X" value={1} hint="since last week" />);
    expect(screen.getByText('since last week')).toBeDefined();
  });

  test('renders children slot content', () => {
    render(
      <StatCard label="Progress" value="50%">
        <div data-testid="embedded" />
      </StatCard>,
    );
    expect(screen.getByTestId('embedded')).toBeDefined();
  });

  test('uses shared stat-card class hooks', () => {
    const { container } = render(<StatCard label="X" value={1} />);
    expect(container.querySelector('.stat-card')).not.toBeNull();
    expect(container.querySelector('.stat-label')).not.toBeNull();
    expect(container.querySelector('.stat-value')).not.toBeNull();
  });
});
