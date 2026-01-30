"""Injectable job runner functions using FastDepends.

These functions are decorated with @inject to automatically resolve
dependencies. They can be called from the JobExecutor or scheduler
after setting up the DependencyContext.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fast_depends import Depends, inject

from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob
from blunder_tutor.background.jobs.backfill_eco import BackfillECOJob
from blunder_tutor.background.jobs.backfill_phases import BackfillPhasesJob
from blunder_tutor.background.jobs.import_games import ImportGamesJob
from blunder_tutor.background.jobs.sync_games import SyncGamesJob
from blunder_tutor.core.dependencies import (
    get_analysis_repository,
    get_context,
    get_event_bus,
    get_game_analyzer,
    get_game_repository,
    get_job_service,
    get_settings_repository,
)
from blunder_tutor.events import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


@inject
async def run_import_job(
    job_id: str,
    source: str,
    username: str,
    max_games: int,
    job_service: Annotated[JobService, Depends(get_job_service)],
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> dict[str, Any]:
    job = ImportGamesJob(
        job_service=job_service,
        settings_repo=settings_repo,
        game_repo=game_repo,
    )
    return await job.execute(
        job_id=job_id,
        source=source,
        username=username,
        max_games=max_games,
    )


@inject
async def run_sync_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
    settings_repo: Annotated[SettingsRepository, Depends(get_settings_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
    event_bus: Annotated[EventBus, Depends(get_event_bus)],
) -> dict[str, Any]:
    job = SyncGamesJob(
        job_service=job_service,
        settings_repo=settings_repo,
        game_repo=game_repo,
        event_bus=event_bus,
    )
    return await job.execute(job_id=job_id)


@inject
async def run_analyze_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    analyzer: Annotated[GameAnalyzer, Depends(get_game_analyzer)],
    game_ids: list[str] | None = None,
    source: str | None = None,
    username: str | None = None,
    steps: list[str] | None = None,
) -> dict[str, Any]:
    job = AnalyzeGamesJob(
        job_service=job_service,
        game_repo=game_repo,
        analysis_repo=analysis_repo,
        analyzer=analyzer,
    )
    return await job.execute(
        job_id=job_id,
        game_ids=game_ids,
        source=source,
        username=username,
        steps=steps,
    )


@inject
async def run_backfill_phases_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> dict[str, Any]:
    ctx = get_context()
    job = BackfillPhasesJob(
        job_service=job_service,
        analysis_repo=analysis_repo,
        game_repo=game_repo,
        engine_path=ctx.engine_path,
    )
    return await job.execute(job_id=job_id)


@inject
async def run_backfill_eco_job(
    job_id: str,
    job_service: Annotated[JobService, Depends(get_job_service)],
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> dict[str, Any]:
    ctx = get_context()
    job = BackfillECOJob(
        job_service=job_service,
        analysis_repo=analysis_repo,
        game_repo=game_repo,
        engine_path=ctx.engine_path,
    )
    return await job.execute(job_id=job_id)


# Mapping of job types to runner functions
JOB_RUNNERS = {
    "import": run_import_job,
    "sync": run_sync_job,
    "analyze": run_analyze_job,
    "backfill_phases": run_backfill_phases_job,
    "backfill_eco": run_backfill_eco_job,
}
