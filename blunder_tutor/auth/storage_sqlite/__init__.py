from __future__ import annotations

from contextlib import AbstractAsyncContextManager

from blunder_tutor.auth.core.protocols import Transaction
from blunder_tutor.auth.storage_sqlite.db import AuthDb
from blunder_tutor.auth.storage_sqlite.repository import (
    IdentityRepository,
    SessionRepository,
    SetupRepository,
    UserRepository,
)


class SqliteStorage:
    def __init__(self, auth_db: AuthDb) -> None:
        self._auth_db = auth_db
        self.users = UserRepository(db=auth_db)
        self.identities = IdentityRepository(db=auth_db)
        self.sessions = SessionRepository(db=auth_db)
        self.setup = SetupRepository(db=auth_db)

    def transaction(self) -> AbstractAsyncContextManager[Transaction]:
        return self._auth_db.transaction()

    @property
    def auth_db(self) -> AuthDb:
        """Escape hatch for lifespan close and the orphan-scan startup hook."""
        return self._auth_db
