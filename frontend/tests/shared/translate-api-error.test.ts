import { describe, it, expect } from 'vitest';
import { ApiError } from '../../src/shared/api';
import { translateSignupError, translateLoginError, translateSlug, translateApiErrorToMessage } from '../../src/shared/translate-api-error';

// Global `t` is stubbed in tests/helpers/setup.ts as identity (key → key).

describe('translateSlug', () => {
  const known = new Set(['known_one']);
  it('maps a known slug to the scoped key', () => {
    expect(translateSlug('auth.signup', new ApiError(400, 'known_one'), known))
      .toBe('auth.signup.error.known_one');
  });
  it('falls back to generic for an unknown slug', () => {
    expect(translateSlug('auth.signup', new ApiError(400, 'mystery'), known))
      .toBe('auth.signup.error_generic');
  });
});

describe('translateSignupError', () => {
  it.each([
    'user_cap_reached', 'invite_code_required', 'invite_code_invalid',
    'username_taken', 'email_taken', 'invalid_username', 'invalid_email', 'invalid_password',
  ])('maps known slug %s', (slug) => {
    expect(translateSignupError(new ApiError(400, slug))).toBe(`auth.signup.error.${slug}`);
  });
  it('falls back to generic for unknown slug', () => {
    expect(translateSignupError(new ApiError(500, 'something_weird'))).toBe('auth.signup.error_generic');
  });
  it('falls back to generic for stale human-string detail', () => {
    expect(translateSignupError(new ApiError(400, 'invalid password'))).toBe('auth.signup.error_generic');
  });
});

describe('translateLoginError', () => {
  it('maps 401 to invalid-credentials', () => {
    expect(translateLoginError(new ApiError(401, 'whatever'))).toBe('auth.login.error_invalid');
  });
  it('falls back to generic for non-401 unknown', () => {
    expect(translateLoginError(new ApiError(500, 'boom'))).toBe('auth.login.error_generic');
  });
});

describe('translateApiErrorToMessage', () => {
  it('surfaces an ApiError message', () => {
    expect(translateApiErrorToMessage(new ApiError(500, 'server fell over'))).toBe('server fell over');
  });
  it('surfaces a plain Error message', () => {
    expect(translateApiErrorToMessage(new Error('Network error'))).toBe('Network error');
  });
  it('falls back to a generic key for an empty ApiError message', () => {
    expect(translateApiErrorToMessage(new ApiError(500, ''))).toBe('common.error_unknown');
  });
  it('falls back to a generic key for a non-error value', () => {
    expect(translateApiErrorToMessage('weird')).toBe('common.error_unknown');
    expect(translateApiErrorToMessage(undefined)).toBe('common.error_unknown');
  });
});
