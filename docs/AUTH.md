# Authentication

Blunder Tutor ships single-user by default. Multi-user login is opt-in.

For the full design contract see [`docs/superpowers/specs/2026-04-17-auth-saas-ready-design.md`](superpowers/specs/2026-04-17-auth-saas-ready-design.md).

## Modes

| `AUTH_MODE` | Behavior | Database layout |
|---|---|---|
| `none` *(default)* | No login. Single user. Identical to pre-auth behavior. | `data/main.sqlite3` |
| `credentials` | Username + password login, capped at `MAX_USERS` accounts. Per-user data isolation. | `data/auth.sqlite3` (shared) + `data/users/<user_id>/main.sqlite3` (per-user) |

Switching modes does **not** migrate data. The legacy `data/main.sqlite3` is only read in `none` mode; existing games/analysis are not imported into a per-user DB automatically.

## Enabling credentials mode

Set at least `AUTH_MODE` and `SECRET_KEY`. Everything else has defaults.

| Variable | Default | Purpose |
|---|---|---|
| `AUTH_MODE` | `none` | Set to `credentials` to enable login. |
| `SECRET_KEY` | — | **Required** in credentials mode. Signs invite codes (HMAC). Opaque; any sufficiently long random string. |
| `MAX_USERS` | `1` | Hard cap on account count. Signups past the cap return 403. |
| `SESSION_MAX_AGE_SECONDS` | `2592000` (30 d) | Absolute session expiry. |
| `SESSION_IDLE_SECONDS` | `604800` (7 d) | Idle-timeout window, refreshed on each request. |
| `AUTH_COOKIE_SECURE` | auto | `true`/`false` to force. Auto = `true` when the request is HTTPS, or when `AUTH_TRUST_PROXY=true` and `X-Forwarded-Proto: https` is present. Set explicitly behind a plain-HTTP-internal proxy that still needs `Secure` on the wire. |
| `AUTH_LOGIN_RATE_LIMIT` | `5` | Login attempts allowed per IP per window. Blocks brute-force and caps bcrypt CPU cost. |
| `AUTH_LOGIN_RATE_WINDOW_SECONDS` | `60` | Login rate-limit window. |
| `AUTH_SIGNUP_RATE_LIMIT` | `3` | Signup attempts allowed per IP per window. |
| `AUTH_SIGNUP_RATE_WINDOW_SECONDS` | `3600` (1 h) | Signup rate-limit window. |
| `AUTH_TRUST_PROXY` | `false` | Honor `X-Forwarded-For` when keying rate limiters. Set `true` only behind a trusted reverse proxy. |

### Docker

```bash
docker run -p 8000:8000 -v $(pwd)/data:/app/data \
  -e AUTH_MODE=credentials \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e MAX_USERS=5 \
  ghcr.io/mrlokans/blunder-tutor:latest
```

### Local

```bash
AUTH_MODE=credentials SECRET_KEY="$(openssl rand -hex 32)" MAX_USERS=5 uv run python main.py
```

Startup validation fails hard (process exits) on: missing `SECRET_KEY`, `MAX_USERS < 1`, or `DEMO_MODE=true` combined with credentials mode.

## First-user signup

The first signup requires a one-time invite code. It is generated automatically on first boot in credentials mode and printed to the server log:

```
Auth invite code: <code>
```

Retrieval options if the log line is lost:

```bash
# Read from the auth DB directly
sqlite3 data/auth.sqlite3 "SELECT value FROM setup WHERE key='invite_code';"

# Or regenerate (invalidates the previous code)
uv run python main.py auth regenerate-invite
```

Navigate to `/setup` (or `/signup` once the instance has users). The invite code is consumed on successful signup; additional users up to `MAX_USERS` sign up via `/signup` without one.

## CLI admin

Gated behind `AUTH_MODE=credentials`:

```bash
uv run python main.py auth list-users
uv run python main.py auth reset-password <username>
# You will be prompted for the new password twice (getpass, no echo).
# For scripted use: pipe the password to stdin with --password-stdin.
echo "new-password" | uv run python main.py auth reset-password <username> --password-stdin
uv run python main.py auth revoke-sessions <username>
uv run python main.py auth delete-user <username>
uv run python main.py auth regenerate-invite
uv run python main.py auth prune-orphans           # delete per-user data dirs with no matching user row
```

## Gotchas

- **Legacy data is not auto-migrated.** Enabling credentials mode on an instance that previously ran `AUTH_MODE=none` leaves `data/main.sqlite3` untouched; it is not visible to any account. Back it up before switching, and re-import games through the new account's UI if you need them.
- **`DEMO_MODE` and credentials mode are mutually exclusive.** Startup aborts rather than letting demo write-blocking silently layer on top of login.
- **Background features are disabled in credentials mode.** Scheduled auto-sync, settings-change notifications, and the job executor run only under `AUTH_MODE=none` at present. Games are fetched and analyzed only via explicit per-user triggers in the UI. Tracked as deferred items in [`docs/superpowers/status/auth-saas-ready.md`](superpowers/status/auth-saas-ready.md).
- **Invite codes are single-use.** Regenerating produces a new code and invalidates the old one. There is no invite inbox — one code exists at a time, used for bootstrapping or operator-driven account creation.
- **`SECRET_KEY` rotation invalidates pending invites.** Any invite generated under the old key fails HMAC verification under the new one. Regenerate after rotation.
- **Passwords reset via CLI only.** There is no email-based reset flow. Losing access to a user requires shell access to the host.
- **Sessions are DB-backed, not JWT.** Revocation (`revoke-sessions`, `delete-user`) takes effect immediately. Horizontal scaling across processes requires a shared `data/` volume.
- **Per-IP rate limits on `/api/auth/login` and `/api/auth/signup` only.** Defaults: 5 logins/min and 3 signups/hour per client IP. Tune via `AUTH_LOGIN_RATE_LIMIT` and `AUTH_SIGNUP_RATE_LIMIT`. No per-username backoff, 2FA, CSRF token, or audit log in MVP. For public instances put the instance behind a reverse proxy, set `AUTH_TRUST_PROXY=true`, and layer additional WAF rate-limiting if you expect distributed brute-force.
- **`AUTH_TRUST_PROXY` defaults to `false`.** With it disabled, the rate limiter keys on the direct client IP. Enable it only when a trusted reverse proxy overwrites `X-Forwarded-For` upstream — a direct-to-uvicorn deploy with `AUTH_TRUST_PROXY=true` lets any client spoof the header and obtain a fresh bucket per forged IP.
- **`data/users/<user_id>/` directories are not self-cleaning.** If the auth DB loses a user row without the deletion path running (e.g., manual SQL), run `auth prune-orphans` — it refuses to run when `users` is empty but `data/users/` is populated (fingerprint of a misconfigured `DB_PATH`).
