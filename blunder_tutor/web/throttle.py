from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_throttle import RateLimiter

if TYPE_CHECKING:
    from blunder_tutor.web.config import AppConfig

# Effectively-unbounded request count for the no-op limiter — used when
# demo mode is off and we want a Pass-through `RateLimiter` instance to
# satisfy the dependency type without actually rate-limiting.
_NOOP_RATE_LIMITER_TIMES = 999_999

_NOOP_LIMITER = RateLimiter(times=_NOOP_RATE_LIMITER_TIMES, seconds=1)


def create_engine_throttle(config: AppConfig) -> RateLimiter:
    if not config.demo_mode:
        return _NOOP_LIMITER

    return RateLimiter(
        times=config.throttle.engine_requests,
        seconds=config.throttle.engine_window_seconds,
        trust_proxy=True,
        add_headers=True,
    )
