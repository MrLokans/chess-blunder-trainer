from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Annotated

import chess.engine
from fastapi import Depends, HTTPException, Request, Response, status

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.base import BaseDbRepository
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import (
    SqliteProfileRepository,
    get_demo_profile_repository,
)
from blunder_tutor.repositories.profile_types import ProfileRepository
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
from blunder_tutor.services.rating_history import RatingHistoryService
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


def get_db_path(request: Request) -> Path:
    """Per-request DB path populated by ``UserDbPathMiddleware``. Treats
    a missing/None value as 401 — by the time a route depends on this,
    `AuthMiddleware` has already enforced auth, so the absence of a
    resolved path is a misconfiguration (route not exempt, but middleware
    skipped) rather than a real unauth case.
    """
    db_path = getattr(request.state, "user_db_path", None)
    if db_path is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    return db_path


get_settings_repository = _repo_dep(SettingsRepository)
get_puzzle_attempt_repository = _repo_dep(PuzzleAttemptRepository)
get_stats_repository = _repo_dep(StatsRepository)
get_job_repository = _repo_dep(JobRepository)
get_game_repository = _repo_dep(GameRepository)
get_analysis_repository = _repo_dep(AnalysisRepository)
get_trap_repository = _repo_dep(TrapRepository)
get_starred_puzzle_repository = _repo_dep(StarredPuzzleRepository)
get_data_management_repository = _repo_dep(DataManagementRepository)


async def get_profile_repository(  # noqa: WPS463 — FastAPI DI factory, not a getter; yields the repo into the request scope.
    request: Request,
) -> AsyncGenerator[ProfileRepository]:
    """Pick the in-memory repo in demo mode; otherwise the per-user
    SQLite-backed implementation. Returns the protocol so handlers
    depend on the contract instead of the concrete class.
    """
    if getattr(request.app.state, "demo_mode", False):
        yield get_demo_profile_repository()
        return
    db_path = get_db_path(request)
    async with SqliteProfileRepository(db_path=db_path) as repo:
        yield repo


async def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> JobService:
    return JobService(job_repository=job_repository, event_bus=event_bus)


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


async def get_rating_history_service(
    profiles: Annotated[ProfileRepository, Depends(get_profile_repository)],
    games: Annotated[GameRepository, Depends(get_game_repository)],
) -> RatingHistoryService:
    return RatingHistoryService(profiles=profiles, games=games)


async def get_puzzle_service(
    trainer: Annotated[Trainer, Depends(get_trainer)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> PuzzleService:
    return PuzzleService(trainer=trainer, analysis_service=analysis_service)


def resolve_user_key(request: Request, config: AppConfig) -> str:
    """Resolve the per-user cache key from the auth context.

    In credentials mode the key is the signed-in user's id; in none mode
    the legacy `config.username` is preserved. The fallback `"default"`
    only applies when neither is set, which only happens for unauthenticated
    flows that should not be hitting cached endpoints anyway.
    """
    ctx = getattr(request.state, "user_ctx", None)
    if ctx is not None:
        return ctx.user_id
    return config.username or "default"


async def set_request_username(
    request: Request,
    config: Annotated[AppConfig, Depends(get_config)],
) -> None:
    """FastAPI dependency: stash the resolved user_key on `request.state`
    so the `@cached` decorator can read it via `resolve_user_key(request)`.
    """
    request.state.username = resolve_user_key(request, config)


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
WorkCoordinatorDep = Annotated[WorkCoordinator, Depends(get_work_coordinator)]
LimitDep = Annotated[chess.engine.Limit, Depends(get_engine_limit)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
TrainerDep = Annotated[Trainer, Depends(get_trainer)]
PuzzleServiceDep = Annotated[PuzzleService, Depends(get_puzzle_service)]
RatingHistoryServiceDep = Annotated[
    RatingHistoryService, Depends(get_rating_history_service)
]
TrapRepoDep = Annotated[TrapRepository, Depends(get_trap_repository)]
StarredPuzzleRepoDep = Annotated[
    StarredPuzzleRepository, Depends(get_starred_puzzle_repository)
]
DataManagementRepoDep = Annotated[
    DataManagementRepository, Depends(get_data_management_repository)
]
ProfileRepoDep = Annotated[ProfileRepository, Depends(get_profile_repository)]


async def check_engine_throttle(request: Request, response: Response) -> None:
    throttle = request.app.state.engine_throttle
    await throttle(request, response)


EngineThrottleDep = Annotated[None, Depends(check_engine_throttle)]
DbPathDep = Annotated[Path, Depends(get_db_path)]
