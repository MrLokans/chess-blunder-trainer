from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from blunder_tutor.auth import AuthService, SqliteStorage


@dataclass(frozen=True, slots=True)
class AuthResources:
    """`app.state.auth` is None under `AUTH_MODE=none`; readers must check before
    dereferencing.

    Holds `Storage` (not the raw `AuthDb`); `AuthConfig` lives on
    `app.state.auth_config` because it exists in both modes."""

    storage: SqliteStorage
    service: AuthService
    db_path: Path
    users_dir: Path
