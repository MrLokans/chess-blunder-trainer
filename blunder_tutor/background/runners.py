"""Injectable job runner functions using FastDepends.

These functions are decorated with @inject to automatically resolve
dependencies. They can be called from the JobExecutor or scheduler
after setting up the DependencyContext.
"""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Annotated, Any

from fast_depends import Depends, inject

from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob
from blunder_tutor.background.jobs.backfill_eco import BackfillECOJob
from blunder_tutor.background.jobs.backfill_phases import BackfillPhasesJob
from blunder_tutor.background.jobs.backfill_tactics import BackfillTacticsJob
from blunder_tutor.background.jobs.backfill_traps import BackfillTrapsJob
from blunder_tutor.background.jobs.delete_all_data import DeleteAllDataJob
from blunder_tutor.background.jobs.import_games import ImportGamesJob
from blunder_tutor.background.jobs.import_pgn import ImportPgnJob
from blunder_tutor.background.jobs.sync_games import SyncGamesJob
from blunder_tutor.constants import (
    JOB_TYPE_ANALYZE,
    JOB_TYPE_BACKFILL_ECO,
    JOB_TYPE_BACKFILL_PHASES,
    JOB_TYPE_BACKFILL_TACTICS,
    JOB_TYPE_BACKFILL_TRAPS,
    JOB_TYPE_DELETE_ALL_DATA,
    JOB_TYPE_IMPORT,
    JOB_TYPE_IMPORT_PGN,
    JOB_TYPE_SYNC,
)
from blunder_tutor.core.dependencies import (
    get_analysis_repository,
    get_context,
    get_data_management_repository,
    get_event_bus,
    get_game_analyzer,
    get_game_repository,
    get_job_service,
    get_settings_repository,
    get_work_coordinator,
)
from blunder_tutor.events import EventBus
from blunder_tutor.events.event_types import TrapsEvent
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.repositories.trap_repository import TrapRepository
from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)

# Type aliases for the FastDepends-injected services. Hoisting these out
# of the parameter lists keeps each runner signature short and avoids
# repeating `Annotated[T, Depends(provider)]` at every site.
JobServiceDep = Annotated[JobService, Depends(get_job_service)]
SettingsRepoDep = Annotated[SettingsRepository, Depends(get_settings_repository)]
GameRepoDep = Annotated[GameRepository, Depends(get_game_repository)]
AnalysisRepoDep = Annotated[AnalysisRepository, Depends(get_analysis_repository)]
EventBusDep = Annotated[EventBus, Depends(get_event_bus)]
GameAnalyzerDep = Annotated[GameAnalyzer, Depends(get_game_analyzer)]
DataManagementRepoDep = Annotated[
    DataManagementRepository, Depends(get_data_management_repository)
]


@inject
async def run_import_job(
    job_id: str,
    source: str,
    username: str,
    max_games: int,
    job_service: JobServiceDep,
    settings_repo: SettingsRepoDep,
    game_repo: GameRepoDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    ctx = get_context()
    job = ImportGamesJob(
        job_service=job_service,
        settings_repo=settings_repo,
        game_repo=game_repo,
        user_id=ctx.user_id,
        event_bus=event_bus,
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
    job_service: JobServiceDep,
    settings_repo: SettingsRepoDep,
    game_repo: GameRepoDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    ctx = get_context()
    job = SyncGamesJob(
        job_service=job_service,
        settings_repo=settings_repo,
        game_repo=game_repo,
        user_id=ctx.user_id,
        event_bus=event_bus,
    )
    return await job.execute(job_id=job_id)


@inject
async def run_analyze_job(
    job_id: str,
    job_service: JobServiceDep,
    game_repo: GameRepoDep,
    analysis_repo: AnalysisRepoDep,
    analyzer: GameAnalyzerDep,
    game_ids: list[str] | None = None,
    source: str | None = None,
    username: str | None = None,
    steps: list[str] | None = None,
) -> dict[str, Any]:
    coordinator = get_work_coordinator()
    event_bus = get_event_bus()
    job = AnalyzeGamesJob(
        job_service=job_service,
        game_repo=game_repo,
        analysis_repo=analysis_repo,
        analyzer=analyzer,
        event_bus=event_bus,
        coordinator=coordinator,
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
    job_service: JobServiceDep,
    analysis_repo: AnalysisRepoDep,
    game_repo: GameRepoDep,
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
    job_service: JobServiceDep,
    analysis_repo: AnalysisRepoDep,
    game_repo: GameRepoDep,
    force: bool = False,
) -> dict[str, Any]:
    ctx = get_context()
    job = BackfillECOJob(
        job_service=job_service,
        analysis_repo=analysis_repo,
        game_repo=game_repo,
        engine_path=ctx.engine_path,
    )
    return await job.execute(job_id=job_id, force=force)


@inject
async def run_delete_all_data_job(
    job_id: str,
    job_service: JobServiceDep,
    data_management_repo: DataManagementRepoDep,
) -> dict[str, Any]:
    job = DeleteAllDataJob(
        job_service=job_service,
        data_management_repo=data_management_repo,
    )
    return await job.execute(job_id=job_id)


@inject
async def run_backfill_tactics_job(
    job_id: str,
    analysis_repo: AnalysisRepoDep,
    game_repo: GameRepoDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    job = BackfillTacticsJob(
        analysis_repo=analysis_repo,
        game_repo=game_repo,
        event_bus=event_bus,
    )
    return await job.execute(job_id=job_id)


@inject
async def run_backfill_traps_job(
    job_id: str,
    job_service: JobServiceDep,
    game_repo: GameRepoDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    ctx = get_context()
    async with TrapRepository(db_path=ctx.db_path) as trap_repo:
        job = BackfillTrapsJob(
            job_service=job_service,
            game_repo=game_repo,
            trap_repo=trap_repo,
        )
        result = await job.execute(job_id=job_id)

        job_record = await job_service.get_job(job_id)
        user_key = (job_record.get("username") if job_record else None) or "default"  # noqa: WPS509 — single parenthesized ternary, `or` short-circuits to default.
        traps_event = TrapsEvent.create_traps_updated(user_key=user_key)
        await event_bus.publish(traps_event)

        return result


@inject
async def run_import_pgn_job(
    job_id: str,
    game_id: str,
    job_service: JobServiceDep,
    game_repo: GameRepoDep,
    analysis_repo: AnalysisRepoDep,
    analyzer: GameAnalyzerDep,
    username: str = "",
) -> dict[str, Any]:
    coordinator = get_work_coordinator()
    event_bus = get_event_bus()
    job = ImportPgnJob(
        job_service=job_service,
        game_repo=game_repo,
        analysis_repo=analysis_repo,
        analyzer=analyzer,
        event_bus=event_bus,
        coordinator=coordinator,
    )
    return await job.execute(job_id=job_id, game_id=game_id, username=username)


# Mapping of job types to runner functions
JOB_RUNNERS = MappingProxyType(
    {
        JOB_TYPE_IMPORT: run_import_job,
        JOB_TYPE_SYNC: run_sync_job,
        JOB_TYPE_ANALYZE: run_analyze_job,
        JOB_TYPE_BACKFILL_PHASES: run_backfill_phases_job,
        JOB_TYPE_BACKFILL_ECO: run_backfill_eco_job,
        JOB_TYPE_BACKFILL_TACTICS: run_backfill_tactics_job,
        JOB_TYPE_BACKFILL_TRAPS: run_backfill_traps_job,
        JOB_TYPE_DELETE_ALL_DATA: run_delete_all_data_job,
        JOB_TYPE_IMPORT_PGN: run_import_pgn_job,
    }
)
