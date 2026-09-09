## Cross-Cutting Concerns (Platform Checklist)

When adding or modifying features, check each of these dimensions:

### Cloud Mode (Billing)
- `CLOUD_MODE=true` (requires `AUTH_MODE=credentials`, incompatible with `DEMO_MODE`) activates Stripe billing: 14-day no-card trial started on signup, subscriptions in a dedicated control-plane DB at `<data_dir>/billing.sqlite3` (versioned via `PRAGMA user_version` — see `blunder_tutor/billing/schema.py`; never touch the auth schema for billing state).
- Entitlements are resolved per-request by `BillingGateMiddleware` (`web/billing_gate.py`) into `request.state.entitlements` + `cloud.*` keys merged into the feature dict by `LocaleMiddleware`. Lapsed users get HTTP 402 on mutations outside `billing_gate.LAPSED_ALLOWED_PREFIXES` — reads always work, data is never deleted on lapse.
- The Stripe webhook (`POST /api/billing/webhook`) is exempt from auth AND CSRF (`web/paths.py` → `BILLING_WEBHOOK_PATH`); it verifies signatures itself and dedups by event id. When adding auth/CSRF exemptions, use `web/paths.py` constants — never middleware-local strings.
- Tests: `tests/billing/` — use the `cloud_app` / `cloud_client` fixtures and `FakeStripeGateway` (`tests/billing/fakes.py`); never construct a real `HttpStripeGateway` in unit tests. The gateway contract suite (`test_gateway_contract.py`) keeps the fake honest — any behavior you add to the fake must be asserted there so the weekly sandbox lane (`.github/workflows/billing-contract.yml`) verifies it against real Stripe. `BillingService` takes an injectable `clock` — drive trial/period boundaries with `ControlledClock`, never `datetime.now` patching.
- E2E: `make test/e2e/cloud` runs `e2e/tests/billing.spec.ts` against `STRIPE_STUB=true` (`billing/stub_gateway.py`: no network, REAL webhook signature verification, subscription state encoded in the subscription id, e.g. `sub_stub_active_monthly`). Never automate the hosted Stripe Checkout page — officially blocked by Stripe.
- Frontend cloud gating: `window.__features['cloud.*']` keys are explicit `true`/`false` under cloud mode and ABSENT in self-host — `hasFeature()`'s missing-key default is `true`, so gate cloud-only UI on `=== true`, never on bare `hasFeature()`.
- Spec: [`docs/superpowers/specs/2026-07-19-saas-launch-design.md`](docs/superpowers/specs/2026-07-19-saas-launch-design.md).
