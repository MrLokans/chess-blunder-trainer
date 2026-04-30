from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse

from blunder_tutor.web.api._debug_render import build_debug_text
from blunder_tutor.web.dependencies import AnalysisRepoDep, GameRepoDep

debug_router = APIRouter()


@debug_router.get(
    "/api/games/{game_id}/debug",
    response_class=PlainTextResponse,
    summary="Get game debug info",
    description="Returns a self-contained debug snapshot of a game with PGN and analysis data.",
)
async def game_debug_info(
    game_id: str,
    game_repo: GameRepoDep,
    analysis_repo: AnalysisRepoDep,
    ply: Annotated[
        int | None,
        Query(description="Ply of the specific blunder being investigated"),
    ] = None,
) -> PlainTextResponse:
    game = await game_repo.get_game(game_id)
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Game not found: {game_id}"
        )

    analysis_moves = await analysis_repo.fetch_moves(game_id)
    eco = await analysis_repo.get_game_eco(game_id)

    return PlainTextResponse(build_debug_text(game, analysis_moves, eco, focus_ply=ply))
