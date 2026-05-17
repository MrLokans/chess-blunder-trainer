from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blunder_tutor.auth import UserContext
    from blunder_tutor.core.dependencies import DependencyContext


def user_scope(ctx: UserContext | DependencyContext) -> str:
    """The single canonical cache scope.

    `ctx.user_id` is the real auth id in `AUTH_MODE=credentials` and the
    fixed `_local` sentinel in `AUTH_MODE=none` (BypassAuthMiddleware on
    every request; the executor's DependencyContext for jobs). Reusing it
    keeps cache isolation identical to data isolation, on both the
    web-request and background-job paths, with no mode special-casing.
    """
    return ctx.user_id
