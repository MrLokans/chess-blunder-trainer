import { useEffect, useState } from 'preact/hooks';
import { ApiError, client, type BillingStatusResponse } from '../shared/api';

async function goTo(promise: Promise<{ url: string }>): Promise<void> {
  const { url } = await promise;
  window.location.assign(url);
}

export function BillingSection() {
  const [status, setStatus] = useState<BillingStatusResponse | null>(null);
  const [hidden, setHidden] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    client.billing
      .status()
      .then(setStatus)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          setHidden(true);
        }
      });
  }, []);

  if (hidden || status === null) {
    return null;
  }

  const subscribe = (plan: 'monthly' | 'annual') => {
    setBusy(true);
    void goTo(client.billing.checkout(plan)).finally(() => { setBusy(false); });
  };

  const openPortal = () => {
    setBusy(true);
    void goTo(client.billing.portal()).finally(() => { setBusy(false); });
  };

  const hasPaidSubscription = status.status === 'active' || status.status === 'past_due';

  return (
    <div data-section="billing" id="billing">
      <hr class="section-divider" />
      <h2 class="settings-section-title">{t('billing.settings.title')}</h2>
      <p>{t(`billing.settings.status_${status.status}`)}</p>
      {hasPaidSubscription ? (
        <button type="button" class="btn" disabled={busy} onClick={openPortal}>
          {t('billing.settings.manage')}
        </button>
      ) : (
        <div class="billing-actions">
          <button
            type="button"
            class="btn"
            disabled={busy}
            onClick={() => { subscribe('monthly'); }}
          >
            {t('billing.settings.subscribe_monthly')}
          </button>
          <button
            type="button"
            class="btn"
            disabled={busy}
            onClick={() => { subscribe('annual'); }}
          >
            {t('billing.settings.subscribe_annual')}
          </button>
        </div>
      )}
    </div>
  );
}
