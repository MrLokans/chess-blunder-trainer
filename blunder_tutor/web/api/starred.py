from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from blunder_tutor.web.dependencies import StarredPuzzleRepoDep

starred_router = APIRouter()


class StarRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class StarredResponse(BaseModel):
    starred: bool


class StarredListResponse(BaseModel):
    items: list[dict[str, Any]]
    total: int


@starred_router.put("/api/starred/{game_id}/{ply}")
async def star_puzzle(
    game_id: str,
    ply: int,
    repo: StarredPuzzleRepoDep,
    body: StarRequest | None = None,
) -> dict[str, bool]:
    note = body.note if body else None
    await repo.star(game_id, ply, note)
    return {"starred": True}


@starred_router.delete("/api/starred/{game_id}/{ply}")
async def unstar_puzzle(
    game_id: str,
    ply: int,
    repo: StarredPuzzleRepoDep,
) -> dict[str, bool]:
    removed = await repo.unstar(game_id, ply)
    if not removed:
        raise HTTPException(status_code=404, detail="Puzzle not starred")
    return {"starred": False}


@starred_router.get("/api/starred/{game_id}/{ply}")
async def check_starred(
    game_id: str,
    ply: int,
    repo: StarredPuzzleRepoDep,
) -> dict[str, bool]:
    is_starred = await repo.is_starred(game_id, ply)
    return {"starred": is_starred}


@starred_router.get("/api/starred")
async def list_starred(
    repo: StarredPuzzleRepoDep,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    items = await repo.list_starred(limit=limit, offset=offset)
    total = await repo.count_starred()
    return {"items": items, "total": total}
