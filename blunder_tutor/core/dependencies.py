"""Core dependency injection module using FastDepends.

This module provides dependency factories that work both in FastAPI routes
(via the web adapter) and in background jobs (via direct injection).
"""

from __future__ import annotations

import contextvars
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fast_depends import Depends

# Runtime imports needed for FastDepends/Pydantic validation
from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.analysis.pipeline.executor import PipelineExecutor
from blunder_tutor.auth import UserId
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.eco_backfill_service import ECOBackfillService
from blunder_tutor.services.job_service import JobService
from blunder_tutor.services.phase_backfill_service import PhaseBackfillService


def _repo_dep[T: BaseDbRepository](cls: type[T]):
    """Same pattern as ``web.dependencies._repo_dep`` but ambient-context:
    the DB path comes from the current ``DependencyContext`` instead of a
    per-request ``Depends(get_db_path)``. Used by the background job
    runner, which doesn't live under a FastAPI request scope.
    """

    async def factory() -> AsyncGenerator[T]:
        ctx = get_context()
        async with cls(db_path=ctx.db_path) as repo:
            yield repo

    factory.__name__ = f"get_{cls.__name__}"
    return factory


@dataclass
class DependencyContext:
    db_path: Path
    event_bus: EventBus
    engine_path: str
    user_id: UserId
    work_coordinator: WorkCoordinator | None = None


_context_var: contextvars.ContextVar[DependencyContext | None] = contextvars.ContextVar(
    "dependency_context", default=None
)


def set_context(context: DependencyContext) -> None:
    _context_var.set(context)


def get_context() -> DependencyContext:
    ctx = _context_var.get()
    if ctx is None:
        raise RuntimeError(
            "Dependency context not initialized. "
            "Call set_context() before using dependencies."
        )
    return ctx


def clear_context() -> None:
    _context_var.set(None)


# --- Repository Dependencies ---

get_job_repository = _repo_dep(JobRepository)
get_settings_repository = _repo_dep(SettingsRepository)
get_game_repository = _repo_dep(GameRepository)
get_analysis_repository = _repo_dep(AnalysisRepository)
get_data_management_repository = _repo_dep(DataManagementRepository)
get_profile_repository = _repo_dep(SqliteProfileRepository)


# --- Service Dependencies ---


async def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> JobService:
    ctx = get_context()
    return JobService(job_repository=job_repository, event_bus=ctx.event_bus)


def get_event_bus() -> EventBus:
    ctx = get_context()
    return ctx.event_bus


def get_work_coordinator() -> WorkCoordinator | None:
    ctx = get_context()
    return ctx.work_coordinator


def get_game_analyzer(
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> GameAnalyzer:
    ctx = get_context()
    return GameAnalyzer(
        analysis_repo=analysis_repo,
        games_repo=game_repo,
        engine_path=ctx.engine_path,
        coordinator=ctx.work_coordinator,
    )


def get_phase_backfill_service(
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> PhaseBackfillService:
    return PhaseBackfillService(
        analysis_repo=analysis_repo,
        game_repo=game_repo,
    )


def get_eco_backfill_service(
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> ECOBackfillService:
    return ECOBackfillService(
        analysis_repo=analysis_repo,
        game_repo=game_repo,
    )


def get_pipeline_executor(
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> PipelineExecutor:
    ctx = get_context()
    return PipelineExecutor(
        analysis_repo=analysis_repo,
        game_repo=game_repo,
        engine_path=ctx.engine_path,
    )
