"""FastAPI dependency injectables for auth.

Only the pieces every auth-aware route needs: pulling the
:class:`UserContext` off ``request.state`` (populated by
:class:`AuthMiddleware`) and surfacing a 401 when it's absent. The
broader blunder_tutor dependency catalogue (per-user repos, services)
stays in ``blunder_tutor/web/dependencies.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from blunder_tutor.auth.core.types import UserContext


def get_user_context(request: Request) -> UserContext:
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return ctx


UserContextDep = Annotated[UserContext, Depends(get_user_context)]
