import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { Badge } from '../../src/components/Badge';

describe('Badge', () => {
  test('renders children', () => {
    render(<Badge>NEW</Badge>);
    expect(screen.getByText('NEW')).toBeDefined();
  });

  test('default variant is neutral', () => {
    render(<Badge>X</Badge>);
    expect(screen.getByText('X').className).toContain('badge--neutral');
  });

  test.each(['primary', 'info', 'warning', 'danger', 'neutral'] as const)(
    'applies %s variant class',
    (variant) => {
      render(<Badge variant={variant}>X</Badge>);
      expect(screen.getByText('X').className).toContain(`badge--${variant}`);
    },
  );

  test('always carries the base badge class', () => {
    render(<Badge variant="info">X</Badge>);
    const cls = screen.getByText('X').className;
    expect(cls).toContain('badge');
    expect(cls).toContain('badge--info');
  });
});
