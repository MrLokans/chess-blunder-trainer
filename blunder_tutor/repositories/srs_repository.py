from __future__ import annotations

from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.srs import CardState, SrsCard


class SrsRepository(BaseDbRepository):
    async def get_card(self, game_id: str, ply: int) -> SrsCard | None:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT game_id, ply, rung, state, due_at, enrolled_at,
                   last_reviewed_at, total_failures
            FROM srs_cards WHERE game_id = ? AND ply = ?
            """,
            (game_id, ply),
        ) as cursor:
            row = await cursor.fetchone()
        return _row_to_card(row) if row else None

    async def upsert_card(self, card: SrsCard) -> None:
        async with self.write_transaction() as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO srs_cards
                    (game_id, ply, rung, state, due_at, enrolled_at,
                     last_reviewed_at, total_failures)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card.game_id,
                    card.ply,
                    card.rung,
                    int(card.state),
                    card.due_at,
                    card.enrolled_at,
                    card.last_reviewed_at,
                    card.total_failures,
                ),
            )

    async def get_due_keys(self, now_iso: str) -> list[tuple[str, int]]:
        conn = await self.get_connection()
        async with conn.execute(
            """
            SELECT game_id, ply FROM srs_cards
            WHERE state = ? AND due_at <= ?
            ORDER BY RANDOM()
            """,
            (int(CardState.ACTIVE), now_iso),
        ) as cursor:
            rows = await cursor.fetchall()
        return [(row["game_id"], row["ply"]) for row in rows]

    async def count_due(self, now_iso: str) -> int:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT COUNT(*) FROM srs_cards WHERE state = ? AND due_at <= ?",
            (int(CardState.ACTIVE), now_iso),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def count_active(self) -> int:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT COUNT(*) FROM srs_cards WHERE state = ?",
            (int(CardState.ACTIVE),),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else 0

    async def next_due_at(self) -> str | None:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT MIN(due_at) FROM srs_cards WHERE state = ?",
            (int(CardState.ACTIVE),),
        ) as cursor:
            row = await cursor.fetchone()
        return row[0] if row else None

    async def active_keys(self) -> set[tuple[str, int]]:
        conn = await self.get_connection()
        async with conn.execute(
            "SELECT game_id, ply FROM srs_cards WHERE state != ?",
            (int(CardState.GRADUATED),),
        ) as cursor:
            rows = await cursor.fetchall()
        return {(row["game_id"], row["ply"]) for row in rows}

    async def delete_all(self) -> int:
        async with self.write_transaction() as conn:
            cursor = await conn.execute("SELECT COUNT(*) FROM srs_cards")
            count = (await cursor.fetchone())[0]
            await conn.execute("DELETE FROM srs_cards")
            return count


def _row_to_card(row: object) -> SrsCard:
    record = dict(row)  # type: ignore[call-overload]
    return SrsCard(
        game_id=record["game_id"],
        ply=record["ply"],
        rung=record["rung"],
        state=CardState(record["state"]),
        due_at=record["due_at"],
        enrolled_at=record["enrolled_at"],
        last_reviewed_at=record["last_reviewed_at"],
        total_failures=record["total_failures"],
    )
