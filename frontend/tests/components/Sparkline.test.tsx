import { describe, test, expect } from 'vitest';
import { render } from '@testing-library/preact';
import { Sparkline } from '../../src/components/Sparkline';

describe('Sparkline', () => {
  test('renders nothing for fewer than two points', () => {
    const { container: empty } = render(<Sparkline values={[]} />);
    expect(empty.firstChild).toBeNull();

    const { container: single } = render(<Sparkline values={[1500]} />);
    expect(single.firstChild).toBeNull();
  });

  test('renders an SVG path for two or more points', () => {
    const { container } = render(<Sparkline values={[1500, 1520]} />);
    const svg = container.querySelector('svg');
    expect(svg).not.toBeNull();
    expect(svg?.getAttribute('role')).toBe('img');
    const path = svg?.querySelector('path');
    expect(path?.getAttribute('d')).toMatch(/^M [\d.]+,[\d.]+ L [\d.]+,[\d.]+$/);
  });

  test('marks an upward trend when the last value is greater than the first', () => {
    const { container } = render(<Sparkline values={[1500, 1480, 1550]} />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('class')).toContain('sparkline--up');
    expect(svg?.getAttribute('class')).not.toContain('sparkline--down');
  });

  test('marks a downward trend when the last value is less than the first', () => {
    const { container } = render(<Sparkline values={[1550, 1500, 1480]} />);
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('class')).toContain('sparkline--down');
    expect(svg?.getAttribute('class')).not.toContain('sparkline--up');
  });

  test('flat series does not divide by zero and stays a valid path', () => {
    const { container } = render(<Sparkline values={[1500, 1500, 1500]} />);
    const path = container.querySelector('path');
    const d = path?.getAttribute('d') ?? '';
    expect(d).toMatch(/^M [\d.]+,[\d.]+ L [\d.]+,[\d.]+ L [\d.]+,[\d.]+$/);
    // No NaN slipped through the projection.
    expect(d).not.toMatch(/NaN/);
  });

  test('forwards aria-label and uses default dimensions', () => {
    const { container } = render(
      <Sparkline values={[1, 2]} ariaLabel="rating trend, blitz" />,
    );
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('aria-label')).toBe('rating trend, blitz');
    expect(svg?.getAttribute('viewBox')).toBe('0 0 120 32');
  });

  test('honours custom width and height props', () => {
    const { container } = render(
      <Sparkline values={[1, 2]} width={200} height={50} />,
    );
    const svg = container.querySelector('svg');
    expect(svg?.getAttribute('viewBox')).toBe('0 0 200 50');
    expect(svg?.getAttribute('width')).toBe('200');
    expect(svg?.getAttribute('height')).toBe('50');
  });
});
