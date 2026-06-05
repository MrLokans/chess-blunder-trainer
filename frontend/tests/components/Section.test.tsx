import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { Section } from '../../src/components/layout/Section';

describe('Section', () => {
  test('renders a section element wrapping its children', () => {
    const { container } = render(<Section><p>body</p></Section>);
    const section = container.querySelector('section');
    expect(section).not.toBeNull();
    expect(section?.querySelector('p')?.textContent).toBe('body');
  });

  test('renders the title as an h2 heading when provided', () => {
    render(<Section title="Engine"><p>x</p></Section>);
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe('Engine');
  });

  test('omits the heading when no title is given', () => {
    const { container } = render(<Section><p>x</p></Section>);
    expect(container.querySelector('h2')).toBeNull();
    expect(container.querySelector('p')?.textContent).toBe('x');
  });
});
