from __future__ import annotations

from blunder_tutor import srs
from blunder_tutor.repositories.srs_repository import SrsRepository
from blunder_tutor.srs import CardState
from blunder_tutor.utils.time import now_iso, utcnow


class SrsService:
    """Blunder Inbox orchestration.

    Review mode is inferred, not declared by the client: an attempt on an
    ACTIVE card is a review (even before its due date — the schedule never
    ignores real evidence); any other failed attempt enrolls the puzzle.
    """

    def __init__(self, srs_repo: SrsRepository) -> None:
        self.srs_repo = srs_repo

    async def on_attempt(self, game_id: str, ply: int, was_correct: bool) -> bool:
        now = utcnow()
        card = await self.srs_repo.get_card(game_id, ply)

        if card is None or card.state is CardState.GRADUATED:
            if not was_correct:
                await self.srs_repo.upsert_card(srs.enroll(game_id, ply, now))
            return False

        if card.state is CardState.SUSPENDED:
            return False

        updated = srs.transition(card, was_correct, now)
        await self.srs_repo.upsert_card(updated)
        return updated.state is CardState.SUSPENDED

    async def pop_due(self) -> tuple[str, int, int]:
        due_keys = await self.srs_repo.get_due_keys(now_iso())
        if not due_keys:
            raise ValueError("No reviews due.")
        game_id, ply = due_keys[0]
        return game_id, ply, len(due_keys)

    async def status(self) -> dict[str, object]:
        return {
            "due": await self.srs_repo.count_due(now_iso()),
            "active": await self.srs_repo.count_active(),
            "next_due_at": await self.srs_repo.next_due_at(),
        }
