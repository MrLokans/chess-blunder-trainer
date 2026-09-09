import { createHmac } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';
import { STUB_WEBHOOK_SECRET } from '../playwright.cloud.config';

const INVITE_FILE = resolve(__dirname, '..', '.tmp-cloud', 'invite.txt');
const PASSWORD = 'password123';

interface MeResponse {
  id: string;
  username: string;
  email: string | null;
}

interface BillingStatus {
  status: string;
  read_only: boolean;
}

function readInvite(): string {
  return readFileSync(INVITE_FILE, 'utf-8').trim();
}

/** Signs a payload exactly as Stripe does (t=<ts>,v1=<hmac-sha256>);
 * the server verifies it with the real verification path. */
function stripeSignature(payload: string): string {
  const ts = String(Math.floor(Date.now() / 1000));
  const digest = createHmac('sha256', STUB_WEBHOOK_SECRET)
    .update(`${ts}.${payload}`)
    .digest('hex');
  return `t=${ts},v1=${digest}`;
}

async function billingStatus(page: Page): Promise<BillingStatus> {
  return (await (await page.request.get('/api/billing/status')).json()) as BillingStatus;
}

async function postWebhook(
  page: Page,
  eventId: string,
  eventType: string,
  data: Record<string, unknown>,
): Promise<number> {
  const payload = JSON.stringify({
    id: eventId,
    object: 'event',
    type: eventType,
    data: { object: data },
  });
  const resp = await page.request.post('/api/billing/webhook', {
    data: payload,
    headers: {
      'content-type': 'application/json',
      'stripe-signature': stripeSignature(payload),
    },
  });
  return resp.status();
}

test.describe('Cloud billing flow (stub gateway)', () => {
  test('trial banner → checkout webhook activates → cancellation goes read-only', async ({
    page,
  }) => {
    const invite = readInvite();

    // 1. First-user signup (invite-gated form on /setup).
    await page.goto('/setup');
    await page.fill('input[name="invite_code"]', invite);
    await page.fill('input[name="username"]', 'alice');
    await page.fill('input[name="password"]', PASSWORD);
    await Promise.all([
      page.waitForURL((url) => ['/', '/setup', '/trainer'].includes(url.pathname)),
      page.click('button[type="submit"]'),
    ]);
    await expect.poll(async () => (await page.request.get('/api/auth/me')).status())
      .toBe(200);
    const me = (await (await page.request.get('/api/auth/me')).json()) as MeResponse;

    // 2. Complete the app setup wizard via API so full-nav pages render.
    const setupDone = await page.request.post('/api/setup/complete');
    expect(setupDone.ok()).toBeTruthy();

    // 3. Fresh signup ⇒ trialing: banner visible, subscribe buttons in
    //    settings, status API agrees.
    await page.goto('/');
    await expect(page.locator('.billing-banner--trial')).toBeVisible();
    const trialStatus = await billingStatus(page);
    expect(trialStatus.status).toBe('trialing');

    await page.goto('/settings');
    const billingSection = page.locator('[data-section="billing"]');
    await expect(billingSection).toBeVisible();
    await expect(
      billingSection.getByRole('button').first(),
    ).toBeVisible();

    // 4. Signed checkout.session.completed webhook activates the
    //    subscription (stub projects state from the encoded sub id).
    const checkoutStatus = await postWebhook(
      page,
      'evt_e2e_checkout',
      'checkout.session.completed',
      {
        client_reference_id: me.id,
        customer: 'cus_stub',
        subscription: 'sub_stub_active_monthly',
      },
    );
    expect(checkoutStatus).toBe(200);
    await expect
      .poll(async () => (await billingStatus(page)).status)
      .toBe('active');

    await page.goto('/');
    await expect(page.locator('.billing-banner--trial')).toBeHidden();
    await expect(page.locator('.billing-banner--lapsed')).toBeHidden();

    // 5. A tampered signature must be rejected.
    const tampered = await page.request.post('/api/billing/webhook', {
      data: JSON.stringify({
        id: 'evt_e2e_forged',
        object: 'event',
        type: 'customer.subscription.deleted',
        data: { object: { id: 'sub_stub_canceled', customer: 'cus_stub' } },
      }),
      headers: {
        'content-type': 'application/json',
        'stripe-signature': 't=1,v1=deadbeef',
      },
    });
    expect(tampered.status()).toBe(400);
    const stillActive = await billingStatus(page);
    expect(stillActive.status).toBe('active');

    // 6. Genuine cancellation (period already over) ⇒ read-only mode:
    //    lapsed banner, mutations blocked with 402, reads fine.
    const cancelStatus = await postWebhook(
      page,
      'evt_e2e_cancel',
      'customer.subscription.deleted',
      { id: 'sub_stub_canceled', customer: 'cus_stub' },
    );
    expect(cancelStatus).toBe(200);
    await expect
      .poll(async () => (await billingStatus(page)).read_only)
      .toBe(true);

    await page.goto('/');
    await expect(page.locator('.billing-banner--lapsed')).toBeVisible();

    const blockedMutation = await page.request.post('/api/settings/board/reset');
    expect(blockedMutation.status()).toBe(402);

    // Lapsed users can still reach billing (to resubscribe) and auth
    // (to leave) — the escape hatches must stay open.
    const checkout = await page.request.post('/api/billing/checkout', {
      data: { plan: 'monthly' },
    });
    expect(checkout.status()).toBe(200);
    const logout = await page.request.post('/api/auth/logout');
    expect(logout.status()).toBe(204);
  });
});
