import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/preact';
import { AuthCard } from '../../src/auth/components/AuthCard';

function setup(props: Partial<Parameters<typeof AuthCard>[0]> = {}) {
  return render(
    <AuthCard title="Sign in" error={null} submitting={false} onSubmit={() => {}} {...props}>
      <input aria-label="username" />
    </AuthCard>,
  );
}

describe('AuthCard', () => {
  it('renders title and children inside a form', () => {
    setup();
    expect(screen.getByRole('heading', { name: 'Sign in' })).toBeDefined();
    expect(screen.getByLabelText('username')).toBeDefined();
  });

  it('renders a polite live-region alert only when error is set', () => {
    const { rerender } = setup();
    expect(screen.queryByRole('alert')).toBeNull();
    rerender(
      <AuthCard title="Sign in" error="Bad creds" submitting={false} onSubmit={() => {}}>
        <input aria-label="username" />
      </AuthCard>,
    );
    const alert = screen.getByRole('alert');
    expect(alert.textContent).toBe('Bad creds');
    expect(alert.getAttribute('aria-live')).toBe('polite');
  });

  it('sets aria-busy on the form while submitting', () => {
    const { container } = setup({ submitting: true });
    expect(container.querySelector('form')?.getAttribute('aria-busy')).toBe('true');
  });

  it('omits aria-busy on the form when not submitting', () => {
    const { container } = setup({ submitting: false });
    expect(container.querySelector('form')?.getAttribute('aria-busy')).toBeNull();
  });

  it('moves focus to the alert region when an error appears', () => {
    const { rerender } = setup();
    rerender(
      <AuthCard title="Sign in" error="Bad creds" submitting={false} onSubmit={() => {}}>
        <input aria-label="username" />
      </AuthCard>,
    );
    const region = document.querySelector('.auth-card [tabindex="-1"]');
    expect(document.activeElement).toBe(region);
  });

  it('calls onSubmit when the form is submitted', () => {
    const onSubmit = vi.fn();
    const { container } = setup({ onSubmit });
    container.querySelector('form')?.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    expect(onSubmit).toHaveBeenCalled();
  });

  it('renders a footer when provided', () => {
    setup({ footer: <a href="/signup">Create account</a> });
    expect(screen.getByText('Create account')).toBeDefined();
  });
});
