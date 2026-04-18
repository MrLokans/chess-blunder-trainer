import { useState } from 'preact/hooks';
import { ApiError, client } from '../shared/api';

export function safeNext(raw: string | null): string {
  // Reject absolute/protocol-relative URLs so `?next=//evil.com` or
  // `?next=https://evil.com` can't bounce the user off-origin after
  // login. Only same-origin paths pass.
  if (!raw) return '/';
  if (!raw.startsWith('/') || raw.startsWith('//') || raw.startsWith('/\\')) {
    return '/';
  }
  return raw;
}

export function LoginForm() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await client.auth.login(username, password);
      const params = new URLSearchParams(window.location.search);
      window.location.href = safeNext(params.get('next'));
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError(t('auth.login.error_invalid'));
      } else {
        setError(t('auth.login.error_generic'));
      }
      setSubmitting(false);
    }
  }

  return (
    <div class="container">
      <div class="auth-card">
        <h1>{t('auth.login.title')}</h1>
        {error && (
          <div class="alert alert-error visible" role="alert">
            {error}
          </div>
        )}
        <form class="auth-form" onSubmit={(e) => { void handleSubmit(e); }}>
          <div class="form-group">
            <label for="username">{t('auth.login.username')}</label>
            <input
              type="text"
              id="username"
              name="username"
              autoComplete="username"
              required
              value={username}
              onInput={(e) => { setUsername(e.currentTarget.value); }}
            />
          </div>
          <div class="form-group">
            <label for="password">{t('auth.login.password')}</label>
            <input
              type="password"
              id="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onInput={(e) => { setPassword(e.currentTarget.value); }}
            />
          </div>
          <button type="submit" class="btn btn-primary" disabled={submitting}>
            {submitting ? t('auth.login.submitting') : t('auth.login.submit')}
          </button>
        </form>
        <div class="auth-footer">
          <a href="/signup">{t('auth.login.need_account')}</a>
        </div>
      </div>
    </div>
  );
}
