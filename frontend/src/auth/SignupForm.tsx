import { useState } from 'preact/hooks';
import { ApiError, client } from '../shared/api';

interface SignupFormProps {
  requireInviteCode?: boolean;
}

// The contract with the backend: these slugs are emitted as HTTP detail
// strings from `/api/auth/signup`. Keeping the set explicit means an i18n
// key typo or a renamed backend error fails loudly in review, not silently
// at runtime via a generic-fallback.
const SIGNUP_ERROR_SLUGS = new Set([
  'user_cap_reached',
  'invite_code_required',
  'invite_code_invalid',
  'username_taken',
  'email_taken',
  'invalid_username',
  'invalid_email',
  'invalid_password',
]);

export function translateSignupError(err: ApiError): string {
  if (typeof err.message === 'string' && SIGNUP_ERROR_SLUGS.has(err.message)) {
    return t(`auth.signup.error.${err.message}`);
  }
  return t('auth.signup.error_generic');
}

export function SignupForm({ requireInviteCode = false }: SignupFormProps) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: Event) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await client.auth.signup({
        username,
        password,
        email: email || undefined,
        invite_code: requireInviteCode ? inviteCode : undefined,
      });
      window.location.href = '/';
    } catch (err) {
      if (err instanceof ApiError) {
        setError(translateSignupError(err));
      } else {
        setError(t('auth.signup.error_generic'));
      }
      setSubmitting(false);
    }
  }

  const titleKey = requireInviteCode ? 'auth.first_setup.title' : 'auth.signup.title';
  const submitKey = requireInviteCode ? 'auth.first_setup.submit' : 'auth.signup.submit';

  return (
    <div class="container">
      <div class="auth-card">
        <h1>{t(titleKey)}</h1>
        {requireInviteCode && (
          <p class="subtitle">{t('auth.first_setup.intro')}</p>
        )}
        {error && (
          <div class="alert alert-error visible" role="alert">
            {error}
          </div>
        )}
        <form class="auth-form" onSubmit={(e) => { void handleSubmit(e); }}>
          {requireInviteCode && (
            <div class="form-group">
              <label for="invite_code">{t('auth.first_setup.invite_code')}</label>
              <input
                type="text"
                id="invite_code"
                name="invite_code"
                autoComplete="off"
                required
                value={inviteCode}
                onInput={(e) => { setInviteCode(e.currentTarget.value); }}
              />
            </div>
          )}
          <div class="form-group">
            <label for="username">{t('auth.signup.username')}</label>
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
            <label for="email">{t('auth.signup.email')}</label>
            <input
              type="email"
              id="email"
              name="email"
              autoComplete="email"
              value={email}
              onInput={(e) => { setEmail(e.currentTarget.value); }}
            />
          </div>
          <div class="form-group">
            <label for="password">{t('auth.signup.password')}</label>
            <input
              type="password"
              id="password"
              name="password"
              autoComplete="new-password"
              required
              minLength={8}
              value={password}
              onInput={(e) => { setPassword(e.currentTarget.value); }}
            />
          </div>
          <button type="submit" class="btn btn-primary" disabled={submitting}>
            {submitting ? t('auth.signup.submitting') : t(submitKey)}
          </button>
        </form>
        {!requireInviteCode && (
          <div class="auth-footer">
            <a href="/login">{t('auth.signup.have_account')}</a>
          </div>
        )}
      </div>
    </div>
  );
}
