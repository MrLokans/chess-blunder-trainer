from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blunder_tutor.analysis.pipeline.context import StepContext, StepResult


class AnalysisStep(ABC):
    @property
    @abstractmethod
    def step_id(self) -> str: ...

    @property
    def depends_on(self) -> frozenset[str]:
        return frozenset()

    @property
    def produces(self) -> frozenset[str]:
        return frozenset({self.step_id})

    @abstractmethod
    async def execute(self, ctx: StepContext) -> StepResult: ...

    async def is_completed(self, ctx: StepContext) -> bool:
        return await ctx.analysis_repo.is_step_completed(ctx.game_id, self.step_id)
