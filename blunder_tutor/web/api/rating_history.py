from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status

from blunder_tutor.cache.decorator import cached
from blunder_tutor.repositories.profile_types import ProfileNotFoundError
from blunder_tutor.utils.time import utcnow
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

# Sliding window applied at the route boundary. Daily bucketing happens in
# the service, so this caps the response at ≤30 points per mode regardless
# of how busy the profile is.
_RATING_HISTORY_WINDOW_DAYS = 30

rating_history_router = APIRouter(dependencies=[Depends(set_request_username)])


@rating_history_router.get(
    "/api/profiles/{profile_id}/rating-history",
    response_model=RatingHistoryResponse,
    summary="Per-time-control rating history for a tracked profile (last 30 days)",
    description=(
        "Returns one rating point per *recorded day* (the last game's rating "
        "for that day) over a fixed 30-day window. `mode` filters by "
        "classified time control. Points are ordered ascending by day."
    ),
)
@cached(
    tag="elo_rating",
    ttl=_ELO_RATING_CACHE_TTL_SECONDS,
    version=1,
    key_params=["profile_id", "mode"],
)
async def get_rating_history(
    request: Request,
    profile_id: int,
    service: RatingHistoryServiceDep,
    mode: str | None = None,
) -> RatingHistoryResponse:
    cutoff = utcnow() - timedelta(days=_RATING_HISTORY_WINDOW_DAYS)
    try:
        points = await service.get(
            profile_id,
            mode=mode,
            since=cutoff.isoformat(),
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
