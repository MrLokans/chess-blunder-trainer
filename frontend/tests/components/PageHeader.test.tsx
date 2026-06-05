import { describe, test, expect } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { PageHeader } from '../../src/components/layout/PageHeader';

describe('PageHeader', () => {
  test('renders the title as an h2', () => {
    render(<PageHeader title="Settings" />);
    const heading = screen.getByRole('heading', { level: 2 });
    expect(heading.textContent).toBe('Settings');
  });

  test('renders the subtitle with the subtitle class when provided', () => {
    const { container } = render(<PageHeader title="Settings" subtitle="Tune things" />);
    const subtitle = container.querySelector('.subtitle');
    expect(subtitle?.textContent).toBe('Tune things');
  });

  test('omits the subtitle node when not provided', () => {
    const { container } = render(<PageHeader title="Settings" />);
    expect(container.querySelector('.subtitle')).toBeNull();
  });

  test('renders actions in a right-aligned row alongside the heading', () => {
    const { container } = render(
      <PageHeader title="Profiles" actions={<button type="button">Add</button>} />,
    );
    const row = container.querySelector('.justify-between');
    expect(row).not.toBeNull();
    expect(row?.querySelector('h2')?.textContent).toBe('Profiles');
    expect(container.querySelector('.page-header__actions button')?.textContent).toBe('Add');
  });

  test('renders the heading without a flex row when there are no actions', () => {
    const { container } = render(<PageHeader title="Profiles" />);
    expect(container.querySelector('.justify-between')).toBeNull();
    expect(container.querySelector('.page-header__actions')).toBeNull();
    expect(screen.getByRole('heading', { level: 2 }).textContent).toBe('Profiles');
  });

  test('wraps everything in a header landmark', () => {
    render(<PageHeader title="Management" subtitle="ops" />);
    expect(screen.getByRole('banner')).not.toBeNull();
  });
});
