from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from blunder_tutor.auth.core.types import UserContext


def get_user_context(request: Request) -> UserContext:
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    return ctx


UserContextDep = Annotated[UserContext, Depends(get_user_context)]
