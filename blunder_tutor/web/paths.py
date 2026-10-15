from __future__ import annotations

# Must be reachable pre-auth; `/logout` is included so revoking a session never
# redirects back to /login with a stale cookie.
AUTH_UI_PATHS: frozenset[str] = frozenset(("/login", "/signup", "/setup", "/logout"))

# Prefix-matched: the session is established under the auth API.
AUTH_API_PREFIX: str = "/api/auth/"
