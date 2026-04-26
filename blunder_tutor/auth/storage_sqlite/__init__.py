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
    """Production :class:`Storage` implementation: bundles the four
    SQLite repos against a shared :class:`AuthDb` and forwards the
    transaction primitive. The auth core only sees this aggregate —
    never ``AuthDb`` directly — so the SQLite specifics live behind
    the Storage seam.
    """

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
        """Escape hatch for code that needs the underlying ``AuthDb``
        (lifespan close, orphan-scan startup hook). Kept narrow so the
        coupling is explicit and visible."""
        return self._auth_db
