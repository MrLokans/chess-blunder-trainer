from __future__ import annotations

from typing import Any

from fastapi import Depends, Request
from fastapi.routing import APIRouter

from blunder_tutor.analysis.traps import (
    TrapDefinition,
    _parse_pgn_to_san,
    get_trap_database,
)
from blunder_tutor.cache.decorator import cached
from blunder_tutor.utils.pgn_utils import extract_game_url_from_string
from blunder_tutor.web.dependencies import TrapRepoDep, set_request_username

traps_router = APIRouter(dependencies=[Depends(set_request_username)])


def _serialize_trap(t: TrapDefinition) -> dict[str, Any]:
    entry_san = [_parse_pgn_to_san(p.pgn) for p in t.positions]
    trap_san = []
    for p in t.positions:
        moves = _parse_pgn_to_san(p.pgn)
        if p.mistake_san:
            moves = [*moves, p.mistake_san]
        trap_san.append(moves)

    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "rating_range": list(t.rating_range),
        "victim_side": t.victim_side,
        "mistake_san": t.mistake_san,
        "refutation_pgn": t.refutation_pgn,
        "refutation_move": t.refutation_move,
        "refutation_note": t.refutation_note,
        "recognition_tip": t.recognition_tip,
        "tags": t.tags,
        "entry_san": entry_san,
        "trap_san": trap_san,
        "refutation_san": _parse_pgn_to_san(t.refutation_pgn),
    }


@traps_router.get("/api/traps/catalog")
@cached(tag="traps", ttl=300, version=1, key_params=[])
async def get_trap_catalog(request: Request) -> list[dict[str, Any]]:
    db = get_trap_database()
    return [_serialize_trap(t) for t in db.all_traps]


@traps_router.get("/api/traps/stats")
@cached(tag="traps", ttl=300, version=1, key_params=[])
async def get_trap_stats(request: Request, trap_repo: TrapRepoDep) -> dict[str, Any]:
    stats = await trap_repo.get_trap_stats()
    summary = await trap_repo.get_trap_summary()

    db = get_trap_database()
    enriched = []
    for s in stats:
        trap_def = db.get_trap(s["trap_id"])
        enriched.append(
            {
                **s,
                "name": trap_def.name if trap_def else s["trap_id"],
                "category": trap_def.category if trap_def else "unknown",
            }
        )

    return {"stats": enriched, "summary": summary}


@traps_router.get("/api/traps/{trap_id}")
@cached(tag="traps", ttl=300, version=1, key_params=["trap_id"])
async def get_trap_detail(
    request: Request, trap_id: str, trap_repo: TrapRepoDep
) -> dict[str, Any]:
    db = get_trap_database()
    trap_def = db.get_trap(trap_id)

    catalog_info = _serialize_trap(trap_def) if trap_def else None

    history = await trap_repo.get_trap_history(trap_id)

    for entry in history:
        pgn = entry.pop("pgn_content", None)
        entry["game_url"] = extract_game_url_from_string(pgn) if pgn else None

    return {"trap": catalog_info, "history": history}
