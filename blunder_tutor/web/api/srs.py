from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from blunder_tutor.web.api import _analysis_schemas as schemas
from blunder_tutor.web.api.analysis import _build_puzzle_response
from blunder_tutor.web.api.schemas import ErrorResponse
from blunder_tutor.web.dependencies import (
    EngineThrottleDep,
    PuzzleServiceDep,
    SrsServiceDep,
)

srs_router = APIRouter()


@srs_router.get(
    "/api/srs/status",
    summary="Review queue status",
    description="Returns due/active counts and the next due timestamp.",
)
async def srs_status(srs_service: SrsServiceDep) -> dict[str, Any]:
    return await srs_service.status()


@srs_router.get(
    "/api/srs/next",
    response_model=schemas.PuzzleResponse,
    responses={404: {"model": ErrorResponse, "description": "No reviews due"}},
    summary="Next due review",
    description=("Returns the next due review puzzle and the remaining due count."),
)
async def srs_next(
    request: Request,
    srs_service: SrsServiceDep,
    puzzle_service: PuzzleServiceDep,
    _throttle: EngineThrottleDep,
) -> dict[str, Any]:
    try:
        game_id, ply, remaining = await srs_service.pop_due()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    puzzle_with_analysis = await puzzle_service.get_specific_puzzle(game_id, ply)
    response = _build_puzzle_response(puzzle_with_analysis, request)
    response["srs"] = {"remaining": remaining}
    return response
