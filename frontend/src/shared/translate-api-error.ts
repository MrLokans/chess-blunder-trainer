import { ApiError } from './api';

// Backend HTTP `detail` slugs. Keeping the sets explicit means an i18n key
// typo or a renamed backend error fails loudly in review, not silently via
// the generic fallback.
const SIGNUP_ERROR_SLUGS: ReadonlySet<string> = new Set([
  'user_cap_reached', 'invite_code_required', 'invite_code_invalid',
  'username_taken', 'email_taken', 'invalid_username', 'invalid_email', 'invalid_password',
]);

// Empty for now; future: 'account_locked', 'email_unverified'.
const LOGIN_ERROR_SLUGS: ReadonlySet<string> = new Set<string>([]);

export function translateSlug(namespace: string, err: ApiError, known: ReadonlySet<string>): string {
  if (typeof err.message === 'string' && known.has(err.message)) {
    return t(`${namespace}.error.${err.message}`);
  }
  return t(`${namespace}.error_generic`);
}

export function translateSignupError(err: ApiError): string {
  return translateSlug('auth.signup', err, SIGNUP_ERROR_SLUGS);
}

export function translateLoginError(err: ApiError): string {
  // Login returns 401 for bad credentials with a non-slug detail; keep the
  // dedicated message. Any future login slugs route through translateSlug.
  if (err.status === 401) return t('auth.login.error_invalid');
  return translateSlug('auth.login', err, LOGIN_ERROR_SLUGS);
}

export function translateApiErrorToMessage(err: unknown): string {
  if (err instanceof ApiError && typeof err.message === 'string' && err.message.length > 0) {
    return err.message;
  }
  if (err instanceof Error && err.message.length > 0) {
    return err.message;
  }
  return t('common.error_unknown');
}
