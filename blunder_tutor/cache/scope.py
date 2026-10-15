from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blunder_tutor.auth import UserContext
    from blunder_tutor.core.dependencies import DependencyContext


def user_scope(ctx: UserContext | DependencyContext) -> str:
    """`ctx.user_id` is the real id in credentials mode and `_local` in none mode, so cache
    isolation matches data isolation."""
    return ctx.user_id
