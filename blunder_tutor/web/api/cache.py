from __future__ import annotations

from fastapi import Depends, Request
from fastapi.routing import APIRouter

from blunder_tutor.cache.invalidation import clear_user_cache
from blunder_tutor.events.event_types import CacheEvent
from blunder_tutor.web.dependencies import EventBusDep, set_request_scope

cache_router = APIRouter(dependencies=[Depends(set_request_scope)])


@cache_router.post(
    "/api/cache/clear",
    summary="Clear the current user's cached aggregates",
    description="Invalidate this user's cached stats/traps/training/elo entries. Other users' caches are untouched.",
)
async def clear_cache(request: Request, event_bus: EventBusDep) -> dict[str, list[str]]:
    scope = request.state.user_scope
    cleared = await clear_user_cache(request.app.state.cache, scope)
    # Same event the automatic invalidator emits, so open dashboards
    # refetch — a manual clear is indistinguishable from an automatic one.
    await event_bus.publish(
        CacheEvent.create_cache_invalidated(scope=scope, tags=cleared)
    )
    return {"cleared": cleared}
