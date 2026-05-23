import { useState } from 'preact/hooks';
import { ApiError, client, isNetworkError } from '../shared/api';
import { translateSignupError } from '../shared/translate-api-error';
import { AuthCard } from './components/AuthCard';
import { FormField } from '../components/FormField';
import { TextInput } from '../components/TextInput';
import { Button } from '../components/Button';

interface SignupFormProps {
  requireInviteCode?: boolean;
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
      if (isNetworkError(err)) setError(t('auth.signup.error_network'));
      else if (err instanceof ApiError) setError(translateSignupError(err));
      else setError(t('auth.signup.error_generic'));
      setSubmitting(false);
    }
  }

  const titleKey = requireInviteCode ? 'auth.first_setup.title' : 'auth.signup.title';
  const submitKey = requireInviteCode ? 'auth.first_setup.submit' : 'auth.signup.submit';

  return (
    <AuthCard
      title={t(titleKey)}
      subtitle={requireInviteCode ? t('auth.first_setup.intro') : undefined}
      error={error}
      submitting={submitting}
      onSubmit={(e) => { void handleSubmit(e); }}
      footer={requireInviteCode ? undefined : <a href="/login">{t('auth.signup.have_account')}</a>}
    >
      {requireInviteCode && (
        <FormField label={t('auth.first_setup.invite_code')} required>
          <TextInput type="text" name="invite_code" autoComplete="off" required
            value={inviteCode} onChange={setInviteCode} />
        </FormField>
      )}
      <FormField label={t('auth.signup.username')} required>
        <TextInput type="text" name="username" autoComplete="username" required
          value={username} onChange={setUsername} />
      </FormField>
      <FormField label={t('auth.signup.email')}>
        <TextInput type="email" name="email" autoComplete="email"
          value={email} onChange={setEmail} />
      </FormField>
      <FormField label={t('auth.signup.password')} required>
        <TextInput type="password" name="password" autoComplete="new-password" required minLength={8}
          value={password} onChange={setPassword} />
      </FormField>
      <Button type="submit" variant="primary" loading={submitting}>
        {submitting ? t('auth.signup.submitting') : t(submitKey)}
      </Button>
    </AuthCard>
  );
}
