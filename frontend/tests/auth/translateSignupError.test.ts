import { describe, it, expect } from 'vitest';
import { ApiError } from '../../src/shared/api';
import { translateSignupError } from '../../src/auth/SignupForm';

// Global `t` is stubbed in tests/helpers/setup.ts as identity (returns
// the key). That's exactly what we need to assert the slug → key mapping.

describe('translateSignupError', () => {
  it.each([
    'user_cap_reached',
    'invite_code_required',
    'invite_code_invalid',
    'username_taken',
    'email_taken',
    'invalid_username',
    'invalid_email',
    'invalid_password',
  ])('maps known slug %s to the scoped i18n key', (slug) => {
    const err = new ApiError(400, slug);
    expect(translateSignupError(err)).toBe(`auth.signup.error.${slug}`);
  });

  it('falls back to generic for unknown slugs', () => {
    const err = new ApiError(500, 'something_weird');
    expect(translateSignupError(err)).toBe('auth.signup.error_generic');
  });

  it('falls back to generic for stale human-string error detail', () => {
    // A pre-stable-slug API would have emitted "invalid password" (with a
    // space) as the detail. The switch must ignore that and fall back.
    const err = new ApiError(400, 'invalid password');
    expect(translateSignupError(err)).toBe('auth.signup.error_generic');
  });
});
