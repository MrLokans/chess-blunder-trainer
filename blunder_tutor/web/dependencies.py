import asyncio
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

import chess.engine
from fastapi import Depends, HTTPException, Request, Response

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.auth.types import UserContext
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.puzzle_attempt_repository import (
    PuzzleAttemptRepository,
)
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.repositories.starred_puzzle_repository import (
    StarredPuzzleRepository,
)
from blunder_tutor.repositories.stats_repository import StatsRepository
from blunder_tutor.repositories.trap_repository import TrapRepository
from blunder_tutor.services.analysis_service import AnalysisService
from blunder_tutor.services.job_service import JobService
from blunder_tutor.services.puzzle_service import PuzzleService
from blunder_tutor.trainer import Trainer
from blunder_tutor.web.config import AppConfig


def _repo_dep[T: BaseDbRepository](cls: type[T]):
    """Generic factory for `Depends(get_db_path)`-scoped repositories.

    Collapses the eight identical "construct → yield → close()" blocks into
    one helper. Every repo extends ``BaseDbRepository`` which already
    supports ``async with``; we just plumb the DI seam through it. Adding
    a new repo is now a single call-site line, not a 6-line factory.
    """

    async def factory(
        db_path: Annotated[Path, Depends(get_db_path)],
    ) -> AsyncGenerator[T]:
        async with cls(db_path=db_path) as repo:
            yield repo

    factory.__name__ = f"get_{cls.__name__}"
    return factory


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


def get_user_context(request: Request) -> UserContext:
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    return ctx


def get_db_path(
    ctx: Annotated[UserContext, Depends(get_user_context)],
) -> Path:
    return ctx.db_path


get_settings_repository = _repo_dep(SettingsRepository)
get_puzzle_attempt_repository = _repo_dep(PuzzleAttemptRepository)
get_stats_repository = _repo_dep(StatsRepository)
get_job_repository = _repo_dep(JobRepository)
get_game_repository = _repo_dep(GameRepository)
get_analysis_repository = _repo_dep(AnalysisRepository)
get_trap_repository = _repo_dep(TrapRepository)
get_starred_puzzle_repository = _repo_dep(StarredPuzzleRepository)
get_data_management_repository = _repo_dep(DataManagementRepository)


async def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> JobService:
    job_service = JobService(job_repository=job_repository, event_bus=event_bus)
    job_service.set_event_loop(asyncio.get_running_loop())
    return job_service


def get_scheduler(
    request: Request,
) -> BackgroundScheduler | None:
    # None when per-user scheduling is deferred (auth credentials mode) —
    # consumers must treat the absent scheduler as a no-op, not an error.
    return request.app.state.scheduler


def get_work_coordinator(request: Request) -> WorkCoordinator:
    return request.app.state.work_coordinator


def get_engine_limit(request: Request) -> chess.engine.Limit:
    return request.app.state.limit


def get_analysis_service(
    coordinator: Annotated[WorkCoordinator, Depends(get_work_coordinator)],
    limit: Annotated[chess.engine.Limit, Depends(get_engine_limit)],
) -> AnalysisService:
    return AnalysisService(coordinator=coordinator, limit=limit)


async def get_trainer(
    games: Annotated[GameRepository, Depends(get_game_repository)],
    attempts: Annotated[
        PuzzleAttemptRepository, Depends(get_puzzle_attempt_repository)
    ],
    analysis: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
) -> Trainer:
    return Trainer(
        games=games,
        attempts=attempts,
        analysis=analysis,
    )


async def get_puzzle_service(
    trainer: Annotated[Trainer, Depends(get_trainer)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> PuzzleService:
    return PuzzleService(trainer=trainer, analysis_service=analysis_service)


async def set_request_username(
    request: Request,
    config: Annotated[AppConfig, Depends(get_config)],
) -> None:
    """Set `request.state.username` as the per-user cache key for
    `@cached` decorators. In credentials mode the key is the signed-in
    user's id so cached results never cross accounts; in none mode the
    legacy `config.username` (or `"default"`) is preserved.
    """
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        request.state.username = ctx.user_id
        return
    request.state.username = config.username or "default"


# Type annotations for dependency injection in route handlers
ConfigDep = Annotated[AppConfig, Depends(get_config)]
EventBusDep = Annotated[EventBus, Depends(get_event_bus)]
SettingsRepoDep = Annotated[SettingsRepository, Depends(get_settings_repository)]
PuzzleAttemptRepoDep = Annotated[
    PuzzleAttemptRepository, Depends(get_puzzle_attempt_repository)
]
StatsRepoDep = Annotated[StatsRepository, Depends(get_stats_repository)]
JobRepoDep = Annotated[JobRepository, Depends(get_job_repository)]
JobServiceDep = Annotated[JobService, Depends(get_job_service)]
GameRepoDep = Annotated[GameRepository, Depends(get_game_repository)]
AnalysisRepoDep = Annotated[AnalysisRepository, Depends(get_analysis_repository)]
OptionalSchedulerDep = Annotated[BackgroundScheduler | None, Depends(get_scheduler)]
WorkCoordinatorDep = Annotated[WorkCoordinator, Depends(get_work_coordinator)]
LimitDep = Annotated[chess.engine.Limit, Depends(get_engine_limit)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
TrainerDep = Annotated[Trainer, Depends(get_trainer)]
PuzzleServiceDep = Annotated[PuzzleService, Depends(get_puzzle_service)]
TrapRepoDep = Annotated[TrapRepository, Depends(get_trap_repository)]
StarredPuzzleRepoDep = Annotated[
    StarredPuzzleRepository, Depends(get_starred_puzzle_repository)
]
DataManagementRepoDep = Annotated[
    DataManagementRepository, Depends(get_data_management_repository)
]


async def check_engine_throttle(request: Request, response: Response) -> None:
    throttle = request.app.state.engine_throttle
    await throttle(request, response)


EngineThrottleDep = Annotated[None, Depends(check_engine_throttle)]
UserContextDep = Annotated[UserContext, Depends(get_user_context)]
DbPathDep = Annotated[Path, Depends(get_db_path)]
