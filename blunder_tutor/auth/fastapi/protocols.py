"""Protocols specific to the FastAPI integration.

Auth core (``blunder_tutor.auth.core``) deliberately knows nothing
about FastAPI — a CLI tool, a Celery worker, or a gRPC service can
import the core surface without dragging FastAPI onto the import
path. Anything that depends on :class:`fastapi.Request` /
:class:`fastapi.Response` lives here instead.
"""

from __future__ import annotations

from typing import Protocol

from fastapi import Request, Response


class RateLimiter(Protocol):
    """Per-IP rate-limit gate, callable as a FastAPI dependency.

    Matches the ``fastapi-throttle`` shape so the production limiter
    drops in directly; alternative implementations (slowapi, no-op)
    that conform to this signature are usable without service-layer
    changes.
    """

    async def __call__(self, request: Request, response: Response) -> None: ...


__all__ = ["RateLimiter"]
