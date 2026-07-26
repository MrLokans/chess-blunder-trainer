import aiosqlite

from blunder_tutor.billing.schema import initialize_billing_schema


async def _table_names(db_path) -> set[str]:
    async with (
        aiosqlite.connect(db_path) as conn,
        conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'") as cur,
    ):
        rows = await cur.fetchall()
    return {row[0] for row in rows}


async def _user_version(db_path) -> int:
    async with (
        aiosqlite.connect(db_path) as conn,
        conn.execute("PRAGMA user_version") as cur,
    ):
        row = await cur.fetchone()
    return row[0]


class TestInitializeBillingSchema:
    async def test_creates_tables(self, tmp_path):
        db_path = tmp_path / "billing.sqlite3"
        await initialize_billing_schema(db_path)
        names = await _table_names(db_path)
        assert {"subscriptions", "webhook_events", "user_nodes"} <= names

    async def test_sets_user_version(self, tmp_path):
        db_path = tmp_path / "billing.sqlite3"
        await initialize_billing_schema(db_path)
        assert await _user_version(db_path) == 1

    async def test_reinit_is_idempotent(self, tmp_path):
        db_path = tmp_path / "billing.sqlite3"
        await initialize_billing_schema(db_path)
        await initialize_billing_schema(db_path)
        assert await _user_version(db_path) == 1
