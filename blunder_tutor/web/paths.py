from __future__ import annotations

# Paths owned by the auth surface that every middleware must let through
# pre-auth: the login/signup/setup pages a logged-out user has to reach,
# plus /logout so revoking a session never redirects back to /login with
# a stale cookie attached. Keep this set in one place so adding a new
# auth page doesn't require touching three middleware modules.
AUTH_UI_PATHS: frozenset[str] = frozenset({"/login", "/signup", "/setup", "/logout"})

# Matched via ``startswith`` — any request under the auth JSON API must be
# reachable without an existing session (the session is being established
# there).
AUTH_API_PREFIX: str = "/api/auth/"
