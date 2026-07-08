"""Leitner-ladder scheduling for the Blunder Inbox review queue.

Pure logic only — no I/O. Persistence lives in
``repositories/srs_repository.py``; orchestration in
``services/srs_service.py``. Design contract:
``docs/superpowers/specs/2026-07-07-srs-blunder-inbox-design.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import IntEnum

LADDER_DAYS: tuple[int, ...] = (1, 3, 7, 16, 35)
LEECH_FAILURE_THRESHOLD = 8


class CardState(IntEnum):
    ACTIVE = 0
    GRADUATED = 1
    SUSPENDED = 2


@dataclass(frozen=True)
class SrsCard:
    game_id: str
    ply: int
    rung: int
    state: CardState
    due_at: str
    enrolled_at: str
    last_reviewed_at: str | None
    total_failures: int


def enroll(game_id: str, ply: int, now: datetime) -> SrsCard:
    return SrsCard(
        game_id=game_id,
        ply=ply,
        rung=0,
        state=CardState.ACTIVE,
        due_at=_due_at(now, rung=0),
        enrolled_at=now.isoformat(),
        last_reviewed_at=None,
        total_failures=1,
    )


def transition(card: SrsCard, passed: bool, now: datetime) -> SrsCard:
    if passed:
        return _climb(card, now)
    return _reset(card, now)


def _climb(card: SrsCard, now: datetime) -> SrsCard:
    reviewed_at = now.isoformat()
    if card.rung >= len(LADDER_DAYS) - 1:
        return replace(card, state=CardState.GRADUATED, last_reviewed_at=reviewed_at)
    next_rung = card.rung + 1
    return replace(
        card,
        rung=next_rung,
        due_at=_due_at(now, next_rung),
        last_reviewed_at=reviewed_at,
    )


def _reset(card: SrsCard, now: datetime) -> SrsCard:
    reviewed_at = now.isoformat()
    failures = card.total_failures + 1
    if failures >= LEECH_FAILURE_THRESHOLD:
        return replace(
            card,
            state=CardState.SUSPENDED,
            total_failures=failures,
            last_reviewed_at=reviewed_at,
        )
    return replace(
        card,
        rung=0,
        due_at=_due_at(now, rung=0),
        total_failures=failures,
        last_reviewed_at=reviewed_at,
    )


def _due_at(now: datetime, rung: int) -> str:
    return (now + timedelta(days=LADDER_DAYS[rung])).isoformat()
