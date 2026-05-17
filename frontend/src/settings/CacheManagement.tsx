import { useState, useCallback } from 'preact/hooks';
import { client } from '../shared/api';
import { Alert } from '../components/Alert';
import { Button } from '../components/Button';

export function CacheManagement() {
  const [clearing, setClearing] = useState(false);
  const [message, setMessage] = useState<{ type: 'error' | 'success'; text: string } | null>(null);

  const handleClear = useCallback(async () => {
    if (!confirm(t('settings.cache.confirm'))) return;
    setMessage(null);
    setClearing(true);
    try {
      await client.cache.clear();
      setMessage({ type: 'success', text: t('settings.cache.cleared_toast') });
    } catch {
      setMessage({ type: 'error', text: t('settings.cache.error') });
    } finally {
      setClearing(false);
    }
  }, []);

  return (
    <section data-section="cache">
      <hr class="section-divider" />
      <h2 class="settings-section-title">{t('settings.cache.title')}</h2>
      <p class="help-text mb-4">{t('settings.cache.description')}</p>
      <Alert type={message?.type ?? 'success'} message={message?.text ?? null} />
      <Button
        variant="danger"
        loading={clearing}
        onClick={() => { void handleClear(); }}
      >
        {t('settings.cache.clear_button')}
      </Button>
    </section>
  );
}
