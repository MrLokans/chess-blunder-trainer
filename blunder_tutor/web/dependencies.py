import asyncio
from typing import Annotated

import chess.engine
from fastapi import Depends, Request

from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob
from blunder_tutor.background.jobs.import_games import ImportGamesJob
from blunder_tutor.background.jobs.sync_games import SyncGamesJob
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
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


def get_settings_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> SettingsRepository:
    return SettingsRepository(
        data_dir=config.data.data_dir,
        db_path=config.data.db_path,
    )


def get_puzzle_attempt_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> PuzzleAttemptRepository:
    return PuzzleAttemptRepository(
        data_dir=config.data.data_dir,
        db_path=config.data.db_path,
    )


def get_stats_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> StatsRepository:
    return StatsRepository(
        data_dir=config.data.data_dir,
        db_path=config.data.db_path,
    )


def get_job_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> JobRepository:
    return JobRepository(
        data_dir=config.data.data_dir,
        db_path=config.data.db_path,
    )


async def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> JobService:
    job_service = JobService(job_repository=job_repository, event_bus=event_bus)
    # Set the event loop for cross-thread event publishing (e.g., from executor threads)
    job_service.set_event_loop(asyncio.get_running_loop())
    return job_service


def get_game_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> GameRepository:
    return GameRepository(
        data_dir=config.data.data_dir,
        db_path=config.data.db_path,
    )


def get_analysis_repository(
    config: Annotated[AppConfig, Depends(get_config)],
) -> AnalysisRepository:
    return AnalysisRepository(
        data_dir=config.data.data_dir,
        db_path=config.data.db_path,
    )


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


def get_trainer(
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


def get_puzzle_service(
    trainer: Annotated[Trainer, Depends(get_trainer)],
    analysis_service: Annotated[AnalysisService, Depends(get_analysis_service)],
) -> PuzzleService:
    return PuzzleService(trainer=trainer, analysis_service=analysis_service)


# Job class dependency providers


def get_analyze_games_job(
    job_service: Annotated[JobService, Depends(get_job_service)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> AnalyzeGamesJob:
    """Provide an AnalyzeGamesJob instance."""
    return AnalyzeGamesJob(
        job_service=job_service,
        game_repo=game_repo,
        analysis_repo=analysis_repo,
        data_dir=config.data.data_dir,
    )


def get_import_games_job(
    job_service: Annotated[JobService, Depends(get_job_service)],
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
    config: Annotated[AppConfig, Depends(get_config)],
) -> ImportGamesJob:
    """Provide an ImportGamesJob instance."""
    return ImportGamesJob(
        job_service=job_service,
        settings_repo=settings_repo,
        game_repo=game_repo,
        data_dir=config.data.data_dir,
    )


def get_sync_games_job(
    job_service: Annotated[JobService, Depends(get_job_service)],
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
    config: Annotated[AppConfig, Depends(get_config)],
    analyze_job: Annotated[AnalyzeGamesJob, Depends(get_analyze_games_job)],
) -> SyncGamesJob:
    """Provide a SyncGamesJob instance with optional analyze job for auto-analysis."""
    return SyncGamesJob(
        job_service=job_service,
        settings_repo=settings_repo,
        game_repo=game_repo,
        data_dir=config.data.data_dir,
        analyze_job=analyze_job,
    )


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

# Job class type annotations
AnalyzeGamesJobDep = Annotated[AnalyzeGamesJob, Depends(get_analyze_games_job)]
ImportGamesJobDep = Annotated[ImportGamesJob, Depends(get_import_games_job)]
SyncGamesJobDep = Annotated[SyncGamesJob, Depends(get_sync_games_job)]
