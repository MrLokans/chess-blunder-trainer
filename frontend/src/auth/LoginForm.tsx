import { useState } from 'preact/hooks';
import { ApiError, client, isNetworkError } from '../shared/api';
import { safeNext } from '../shared/safe-redirect';
import { translateLoginError } from '../shared/translate-api-error';
import { AuthCard } from './components/AuthCard';
import { FormField } from '../components/FormField';
import { TextInput } from '../components/TextInput';
import { Button } from '../components/Button';

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
      if (isNetworkError(err)) setError(t('auth.login.error_network'));
      else if (err instanceof ApiError) setError(translateLoginError(err));
      else setError(t('auth.login.error_generic'));
      setSubmitting(false);
    }
  }

  return (
    <AuthCard
      title={t('auth.login.title')}
      error={error}
      submitting={submitting}
      onSubmit={(e) => { void handleSubmit(e); }}
      footer={<a href="/signup">{t('auth.login.need_account')}</a>}
    >
      <FormField label={t('auth.login.username')} required>
        <TextInput type="text" name="username" autoComplete="username" required
          value={username} onChange={setUsername} />
      </FormField>
      <FormField label={t('auth.login.password')} required>
        <TextInput type="password" name="password" autoComplete="current-password" required
          value={password} onChange={setPassword} />
      </FormField>
      <Button type="submit" variant="primary" loading={submitting}>
        {submitting ? t('auth.login.submitting') : t('auth.login.submit')}
      </Button>
    </AuthCard>
  );
}
