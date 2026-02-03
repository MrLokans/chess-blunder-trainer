import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated

import chess.engine
from fastapi import Depends, Request

from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.puzzle_attempt_repository import (
    PuzzleAttemptRepository,
)
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.repositories.stats_repository import StatsRepository
from blunder_tutor.services.analysis_service import AnalysisService
from blunder_tutor.services.job_service import JobService
from blunder_tutor.services.puzzle_service import PuzzleService
from blunder_tutor.trainer import Trainer
from blunder_tutor.web.config import AppConfig


def get_config(request: Request) -> AppConfig:
    return request.app.state.config


def get_event_bus(request: Request) -> EventBus:
    return request.app.state.event_bus


async def get_settings_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[SettingsRepository]:
    repo = SettingsRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_puzzle_attempt_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[PuzzleAttemptRepository]:
    repo = PuzzleAttemptRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_stats_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[StatsRepository]:
    repo = StatsRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_job_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[JobRepository]:
    repo = JobRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> JobService:
    job_service = JobService(job_repository=job_repository, event_bus=event_bus)
    job_service.set_event_loop(asyncio.get_running_loop())
    return job_service


async def get_game_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[GameRepository]:
    repo = GameRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_analysis_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[AnalysisRepository]:
    repo = AnalysisRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_data_management_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AsyncGenerator[DataManagementRepository]:
    repo = DataManagementRepository(db_path=config.data.db_path)
    try:
        yield repo
    finally:
        await repo.close()


def get_scheduler(
    request: Request,
) -> BackgroundScheduler:
    return request.app.state.scheduler


def get_engine(request: Request) -> chess.engine.UciProtocol:
    return request.app.state.engine


def get_engine_limit(request: Request) -> chess.engine.Limit:
    return request.app.state.limit


def get_analysis_service(
    engine: Annotated[chess.engine.UciProtocol, Depends(get_engine)],
    limit: Annotated[chess.engine.Limit, Depends(get_engine_limit)],
) -> AnalysisService:
    return AnalysisService(engine=engine, limit=limit)


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
SchedulerDep = Annotated[BackgroundScheduler, Depends(get_scheduler)]
EngineDep = Annotated[chess.engine.UciProtocol, Depends(get_engine)]
LimitDep = Annotated[chess.engine.Limit, Depends(get_engine_limit)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(get_analysis_service)]
TrainerDep = Annotated[Trainer, Depends(get_trainer)]
PuzzleServiceDep = Annotated[PuzzleService, Depends(get_puzzle_service)]
DataManagementRepoDep = Annotated[
    DataManagementRepository, Depends(get_data_management_repository)
]
