from __future__ import annotations

import asyncio
from collections.abc import Callable

import pytest
from fastapi import Request

from blunder_tutor.auth import UserContext
from blunder_tutor.cache.backend import InMemoryCacheBackend
from blunder_tutor.cache.decorator import cached
from blunder_tutor.cache.invalidation import CACHE_TAGS, CacheInvalidator
from blunder_tutor.cache.scope import user_scope
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import (
    EloRatingEvent,
    Event,
    StatsEvent,
    TrainingEvent,
    TrapsEvent,
)
from tests.helpers.cache import make_user_ctx, scoped_request

# Each logical cache tag paired with the publisher that, in production,
# announces that that aggregate changed. The invariant: the tag the
# write path stores under MUST equal the tag the invalidator derives
# from this publisher's event, for the same resolved context.
_PUBLISHERS: dict[str, Callable[[str], Event]] = {
    "stats": lambda s: StatsEvent.create_stats_updated(scope=s),
    "traps": lambda s: TrapsEvent.create_traps_updated(scope=s),
    "training": lambda s: TrainingEvent.create_training_updated(scope=s),
    "elo_rating": lambda s: EloRatingEvent.create_elo_rating_updated(
        scope=s, trigger="game_sync_completed"
    ),
}

_CREDENTIALS_CTX = make_user_ctx("11111111-1111-1111-1111-111111111111", "alice")
_NONE_CTX = make_user_ctx("_local", "_local")


def test_every_registered_tag_has_a_publisher() -> None:
    # If a tag enters CACHE_TAGS without a publisher here, the matrix
    # below silently stops covering it — fail loudly instead.
    assert set(_PUBLISHERS) == CACHE_TAGS


@pytest.mark.parametrize(
    "ctx", [_NONE_CTX, _CREDENTIALS_CTX], ids=["none", "credentials"]
)
@pytest.mark.parametrize("logical_tag", sorted(_PUBLISHERS))
class TestKeyAgreementInvariant:
    """Regression lock for the shipped defect: caches were written under
    one scope derivation and invalidated under another, so background
    work never cleared them in credentials mode. This drives BOTH sides
    from the same resolved context through the production resolver."""

    async def test_publisher_event_invalidates_the_written_entry(
        self, ctx: UserContext, logical_tag: str
    ) -> None:
        backend = InMemoryCacheBackend()
        bus = EventBus()
        calls = 0

        @cached(tag=logical_tag, ttl=300, version=1, key_params=[])
        async def endpoint(request: Request) -> dict:
            nonlocal calls
            calls += 1
            return {"n": calls}

        request = await scoped_request(ctx, backend)

        assert (await endpoint(request=request))["n"] == 1
        assert (await endpoint(request=request))["n"] == 1  # served cached

        invalidator = CacheInvalidator(cache=backend, event_bus=bus)
        await invalidator.start()
        await bus.publish(_PUBLISHERS[logical_tag](user_scope(ctx)))
        await asyncio.sleep(0.05)
        await invalidator.stop()

        # Recomputed → the write-path tag and the invalidator tag agreed.
        # On the shipped bug this stayed cached at n == 1.
        assert (await endpoint(request=request))["n"] == 2
