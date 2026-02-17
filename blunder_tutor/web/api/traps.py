from __future__ import annotations

from typing import Any

from fastapi.routing import APIRouter

from blunder_tutor.analysis.traps import (
    TrapDefinition,
    _parse_pgn_to_san,
    get_trap_database,
)
from blunder_tutor.web.dependencies import TrapRepoDep

traps_router = APIRouter()


def _serialize_trap(t: TrapDefinition) -> dict[str, Any]:
    return {
        "id": t.id,
        "name": t.name,
        "category": t.category,
        "rating_range": list(t.rating_range),
        "victim_side": t.victim_side,
        "mistake_ply": t.mistake_ply,
        "mistake_san": t.mistake_san,
        "refutation_pgn": t.refutation_pgn,
        "refutation_move": t.refutation_move,
        "refutation_note": t.refutation_note,
        "recognition_tip": t.recognition_tip,
        "tags": t.tags,
        "entry_san_variants": t.entry_san_variants,
        "trap_san_variants": t.trap_san_variants,
        "refutation_san": _parse_pgn_to_san(t.refutation_pgn),
    }


@traps_router.get("/api/traps/catalog")
async def get_trap_catalog() -> list[dict[str, Any]]:
    db = get_trap_database()
    return [_serialize_trap(t) for t in db.all_traps]


@traps_router.get("/api/traps/stats")
async def get_trap_stats(trap_repo: TrapRepoDep) -> dict[str, Any]:
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
async def get_trap_detail(trap_id: str, trap_repo: TrapRepoDep) -> dict[str, Any]:
    db = get_trap_database()
    trap_def = db.get_trap(trap_id)

    catalog_info = _serialize_trap(trap_def) if trap_def else None

    history = await trap_repo.get_trap_history(trap_id)

    return {"trap": catalog_info, "history": history}
