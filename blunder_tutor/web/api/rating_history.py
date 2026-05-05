from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status

from blunder_tutor.cache.decorator import cached
from blunder_tutor.repositories.profile_types import ProfileNotFoundError
from blunder_tutor.web.api._profile_schemas import (
    RatingHistoryResponse,
    RatingPointShape,
)
from blunder_tutor.web.dependencies import (
    RatingHistoryServiceDep,
    set_request_username,
)

# 5 minutes — same default as the stats/traps caches; bounded by event-driven
# invalidation, so the TTL just caps how long stale data can survive in the
# unlikely event of a missed event.
_ELO_RATING_CACHE_TTL_SECONDS = 300

rating_history_router = APIRouter(dependencies=[Depends(set_request_username)])


@rating_history_router.get(
    "/api/profiles/{profile_id}/rating-history",
    response_model=RatingHistoryResponse,
    summary="Per-time-control rating history for a tracked profile",
    description=(
        "Returns one rating point per game derived from PGN headers "
        "(`WhiteElo` / `BlackElo`). Optional `mode` filters by classified "
        "time control; optional `since` (ISO 8601) lower-bounds "
        "`end_time_utc`. Results are ordered ascending by game time."
    ),
)
@cached(
    tag="elo_rating",
    ttl=_ELO_RATING_CACHE_TTL_SECONDS,
    version=1,
    key_params=["profile_id", "mode", "since"],
)
async def get_rating_history(
    request: Request,
    profile_id: int,
    service: RatingHistoryServiceDep,
    mode: str | None = None,
    since: datetime | None = None,
) -> RatingHistoryResponse:
    try:
        points = await service.get(
            profile_id,
            mode=mode,
            since=since.isoformat() if since is not None else None,
        )
    except ProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="profile not found",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return RatingHistoryResponse(
        points=[
            RatingPointShape(
                end_time_utc=p.end_time_utc,
                rating=p.rating,
                game_type=p.game_type,
                color=p.color,
                opponent_rating=p.opponent_rating,
            )
            for p in points
        ]
    )
