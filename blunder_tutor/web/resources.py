from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from blunder_tutor.auth import AuthService, SqliteStorage


@dataclass(frozen=True, slots=True)
class AuthResources:
    """Credentials-mode auth bundle. Materialized in the
    ``_bootstrap_auth`` lifespan phase and assigned to
    ``app.state.auth``.

    Existence is mode-coupled: ``app.state.auth`` is ``None`` under
    ``AUTH_MODE=none`` and an ``AuthResources`` after the lifespan
    bootstrap completes under ``AUTH_MODE=credentials``. Readers MUST
    check ``if app.state.auth is not None:`` before dereferencing —
    making the optionality explicit is the whole point of this type, so
    a future agent reading ``app.state.auth.service`` in a code path
    reachable from none-mode fails type-check instead of failing at the
    unlucky request.

    Holding ``storage`` (not the raw ``AuthDb``) means every consumer
    goes through the :class:`Storage` Protocol — repos, transaction —
    so a future backend swap is isolated to the ``_bootstrap_auth``
    construction site. Code that genuinely needs the underlying
    ``AuthDb`` (lifespan close) reaches it via ``storage.auth_db``,
    keeping the SQLite coupling visible in one narrow escape hatch.

    AuthConfig deliberately lives at ``app.state.auth_config`` instead
    of as a field here: it is set in *both* modes and several middleware
    read it without mode dispatch (e.g. ``SecurityHeadersMiddleware``).
    Hanging it off `auth` would force every reader to handle `auth is None`.
    """

    storage: SqliteStorage
    service: AuthService
    db_path: Path
    users_dir: Path
