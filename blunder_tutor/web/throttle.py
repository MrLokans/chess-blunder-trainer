from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi_throttle import RateLimiter

if TYPE_CHECKING:
    from blunder_tutor.web.config import AppConfig

_NOOP_LIMITER = RateLimiter(times=999_999, seconds=1)


def create_engine_throttle(config: AppConfig) -> RateLimiter:
    if not config.demo_mode:
        return _NOOP_LIMITER

    return RateLimiter(
        times=config.throttle.engine_requests,
        seconds=config.throttle.engine_window_seconds,
        trust_proxy=True,
        add_headers=True,
    )
