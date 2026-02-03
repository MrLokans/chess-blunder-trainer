"""Core dependency injection module using FastDepends.

This module provides dependency factories that work both in FastAPI routes
(via the web adapter) and in background jobs (via direct injection).
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from fast_depends import Depends

# Runtime imports needed for FastDepends/Pydantic validation
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.analysis.pipeline import PipelineExecutor
from blunder_tutor.events import EventBus
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.data_management import DataManagementRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.eco_backfill_service import ECOBackfillService
from blunder_tutor.services.job_service import JobService
from blunder_tutor.services.phase_backfill_service import PhaseBackfillService


@dataclass
class DependencyContext:
    db_path: Path
    event_bus: EventBus
    engine_path: str


# Global context - set by the application or job executor before use
_context: DependencyContext | None = None


def set_context(context: DependencyContext) -> None:
    global _context
    _context = context


def get_context() -> DependencyContext:
    if _context is None:
        raise RuntimeError(
            "Dependency context not initialized. "
            "Call set_context() before using dependencies."
        )
    return _context


def clear_context() -> None:
    """Clear the global dependency context."""
    global _context
    _context = None


# --- Repository Dependencies ---


async def get_job_repository() -> AsyncGenerator[JobRepository]:
    ctx = get_context()
    repo = JobRepository(db_path=ctx.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_settings_repository() -> AsyncGenerator[SettingsRepository]:
    ctx = get_context()
    repo = SettingsRepository(db_path=ctx.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_game_repository() -> AsyncGenerator[GameRepository]:
    ctx = get_context()
    repo = GameRepository(db_path=ctx.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_analysis_repository() -> AsyncGenerator[AnalysisRepository]:
    ctx = get_context()
    repo = AnalysisRepository(db_path=ctx.db_path)
    try:
        yield repo
    finally:
        await repo.close()


async def get_data_management_repository() -> AsyncGenerator[DataManagementRepository]:
    ctx = get_context()
    repo = DataManagementRepository(db_path=ctx.db_path)
    try:
        yield repo
    finally:
        await repo.close()


# --- Service Dependencies ---


async def get_job_service(
    job_repository: Annotated[JobRepository, Depends(get_job_repository)],
) -> JobService:
    ctx = get_context()
    job_service = JobService(job_repository=job_repository, event_bus=ctx.event_bus)
    job_service.set_event_loop(asyncio.get_running_loop())
    return job_service


def get_event_bus() -> EventBus:
    ctx = get_context()
    return ctx.event_bus


def get_game_analyzer(
    analysis_repo: Annotated[AnalysisRepository, Depends(get_analysis_repository)],
    game_repo: Annotated[GameRepository, Depends(get_game_repository)],
) -> GameAnalyzer:
    ctx = get_context()
    return GameAnalyzer(
        analysis_repo=analysis_repo,
        games_repo=game_repo,
        engine_path=ctx.engine_path,
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
