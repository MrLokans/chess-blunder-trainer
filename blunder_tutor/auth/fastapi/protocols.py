from __future__ import annotations

from typing import Protocol

from fastapi import Request, Response


class RateLimiter(Protocol):
    """Signature matches `fastapi-throttle`."""

    async def __call__(self, request: Request, response: Response) -> None: ...


__all__ = ["RateLimiter"]
