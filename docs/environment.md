# Environment Variables

Operator-facing reference for every environment variable Blunder Tutor reads at startup. All variables are optional unless a default is shown as `(required)`.

Values shown in the **Default** column reflect the actual code (`blunder_tutor/web/config.py` and `blunder_tutor/observability/config.py`) — if you find a drift between this doc and the code, treat the code as authoritative and open an issue.

Booleans accept `1`, `true`, `yes`, `on` (case-insensitive) for "true"; everything else (including unset) is "false".

---

## Authentication

Active only when `AUTH_MODE=credentials`. The `none` default is single-user with no login.

| Var | Default | Purpose |
|---|---|---|
| `AUTH_MODE` | `none` | `none` — single-user, no login. `credentials` — multi-user with username/password and per-user SQLite. |
| `SECRET_KEY` | (required when `AUTH_MODE=credentials`) | Used for HMAC of invite codes and (future) CSRF tokens. Must be ≥ 64 hex chars (the output of `openssl rand -hex 32`). |
| `MAX_USERS` | `1` | Cap on signups. Once reached, signup endpoints return 403. |
| `SESSION_MAX_AGE_SECONDS` | `2592000` (30 days) | Absolute session lifetime. |
| `SESSION_IDLE_SECONDS` | `604800` (7 days) | Idle expiry. Must be ≤ `SESSION_MAX_AGE_SECONDS`. |
| `AUTH_COOKIE_SECURE` | unset (auto-derive) | Tri-state. Unset: derive from request scheme + `VITE_DEV`. `true` / `false`: explicit override (set `true` behind a TLS-terminating proxy where the request still arrives over HTTP). |
| `AUTH_LOGIN_RATE_LIMIT` | `5` | Per-IP login attempts allowed in `AUTH_LOGIN_RATE_WINDOW_SECONDS`. Caps bcrypt CPU cost on the login path. |
| `AUTH_LOGIN_RATE_WINDOW_SECONDS` | `60` | Login rate-limit window. |
| `AUTH_SIGNUP_RATE_LIMIT` | `3` | Per-IP signup attempts allowed in `AUTH_SIGNUP_RATE_WINDOW_SECONDS`. |
| `AUTH_SIGNUP_RATE_WINDOW_SECONDS` | `3600` | Signup rate-limit window. |
| `AUTH_TRUST_PROXY` | `false` | When `true`, rate limiters key on `X-Forwarded-For`. **Security-critical:** must stay `false` for direct-to-uvicorn deploys. Set `true` only behind a reverse proxy that overwrites the header (e.g. nginx `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`). |
| `AUTH_BCRYPT_COST` | unset (library default, currently 12) | Bcrypt cost factor (rounds). Range `4`–`31`. Higher = stronger but slower. The test suite forces `4` to keep wall time bounded. |

See [`docs/AUTH.md`](AUTH.md) for the multi-user setup walkthrough and CLI admin commands.

---

## Data & Hosts

| Var | Default | Purpose |
|---|---|---|
| `DB_PATH` | `data/main.sqlite3` | SQLite database path in `none` mode. Ignored in `credentials` mode (per-user DBs are materialized under `users_dir/<user_id>/main.sqlite3`). |
| `BLUNDER_TUTOR_DB_PATH` | unset | Alias for `DB_PATH` honored by the `blunder-tutor-db` migration CLI. |
| `STOCKFISH_BINARY` | auto-detect | Path to the Stockfish binary. If unset, the app probes `/usr/games/stockfish`, `/usr/local/bin/stockfish`, `/usr/bin/stockfish` in order and fails if none exists. |
| `ALLOWED_HOSTS` | `*` | Comma-separated `Host` header allowlist passed to `TrustedHostMiddleware`. The `*` default accepts any Host — appropriate for single-tenant self-hosted instances. **Multi-tenant or shared-vhost deploys MUST set this** (e.g. `example.com,www.example.com`) to prevent Host-header spoofing from defeating the CSRF Origin check. |

---

## Demo Mode

Hosted-demo guardrails. When `DEMO_MODE=true`, all mutation endpoints return 403 (see `DEMO_BLOCKED_ROUTES` in `blunder_tutor/web/middleware.py`).

| Var | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `false` | Enables read-only demo mode. Cannot be combined with `AUTH_MODE=credentials`. |
| `DEMO_THROTTLE_RATE` | unset | Format: `<requests>/<seconds>`, e.g. `10/60`. Caps engine-analysis requests per IP. Empty/unset uses the in-code defaults (`engine_requests=10`, `engine_window_seconds=60`). |

---

## Cache

In-memory response cache for read endpoints.

| Var | Default | Purpose |
|---|---|---|
| `CACHE_ENABLED` | `true` | Master switch. `false` disables all caching. |
| `CACHE_DEFAULT_TTL` | `300` | Default TTL in seconds for cache entries that don't override it. |

---

## Frontend Dev Mode

| Var | Default | Purpose |
|---|---|---|
| `VITE_DEV` | `false` | When `true`, the FastAPI server expects a Vite dev server at the conventional port and serves frontend assets from there (HMR mode). Two-terminal local-dev workflow: `uv run python main.py` + `VITE_DEV=true npm run dev`. |

---

## Analytics (Plausible)

Opt-in privacy-preserving analytics. Off by default.

| Var | Default | Purpose |
|---|---|---|
| `PLAUSIBLE_DOMAIN` | unset | Your Plausible site domain. Setting this enables the analytics snippet. |
| `PLAUSIBLE_SCRIPT_URL` | `https://plausible.io/js/script.js` | Override if you self-host Plausible. |

---

## Observability (Sentry)

Off by default. The two-knob activation is `SENTRY_ENABLED=true` plus `SENTRY_DSN=<dsn>`. When disabled, every facade primitive in `blunder_tutor.observability` is a zero-cost no-op — no SDK init, no background thread, no network calls.

### Activation

| Var | Default | Purpose |
|---|---|---|
| `SENTRY_ENABLED` | `false` | Master switch. Required `true` to activate. |
| `SENTRY_DSN` | unset | Sentry project DSN. Required when `SENTRY_ENABLED=true` — startup fails loudly if it's unset. |

### Tuning

| Var | Default | Purpose |
|---|---|---|
| `SENTRY_ENVIRONMENT` | `dev` | Sentry environment tag. Set explicitly per deploy (`production`, `staging`, `demo`). |
| `SENTRY_RELEASE` | unset | Release tag (e.g. CI git SHA). No fallback — leaving it unset means events have no release attached. |
| `SENTRY_TRACES_SAMPLE_RATE` | `1.0` | Per-trace sampling, range `0.0`–`1.0`. Low-traffic instances keep `1.0`. |
| `SENTRY_SEND_DEFAULT_PII` | `false` | When `true`, attaches client IPs, structured cookies, request bodies, and authenticated user IDs to events. |
| `SENTRY_TRACE_HEALTH` | `false` | When `true`, includes `/health` and `/static/*` paths in trace ingestion (use when debugging Docker healthcheck failures). |

### Sentry Crons monitor setup

The scheduler runs `_fanout_tick` every 5 minutes. The code is decorated with `@sentry_sdk.monitor(monitor_slug="bt-scheduler-tick")`, so once Sentry is enabled the tick reports check-ins automatically. To get alerted when a check-in is missed, create the matching monitor configuration in Sentry:

1. In Sentry → **Crons** → **Add Monitor**.
2. **Slug:** `bt-scheduler-tick` (must match exactly).
3. **Schedule:** crontab `*/5 * * * *` (every 5 minutes).
4. **Check-in margin (grace period):** 1 minute.
5. **Max runtime:** 5 minutes (a tick that runs longer than its own interval is the alert worth waking up for).
6. **Notifications:** route to whatever you use for ops alerts.

A missed check-in means the scheduler is wedged — auto-sync has stopped for every user on this instance until the process is restarted.

### Data handling

The SDK runs an `EventScrubber` with the project denylist (sessions, invite codes, CSRF tokens, plus Sentry's defaults for passwords / tokens / cookies / Authorization headers). The bar is "do not ship known secrets," not full GDPR-grade redaction. Operators with strict requirements should review the data themselves before pointing a production DSN at this.

See [`docs/architecture/decisions/003-opt-in-sentry-observability.md`](architecture/decisions/003-opt-in-sentry-observability.md) for the design rationale and [`docs/conventions/observability.md`](conventions/observability.md) for the metrics-tag cardinality rules followed by call sites.

---

## Debugging

| Var | Default | Purpose |
|---|---|---|
| `BLUNDER_TUTOR_DEBUG_EVENTS` | `false` | When `true`, the in-process `EventBus` logs every published / consumed event. Useful when chasing event-routing issues; noisy otherwise. |
