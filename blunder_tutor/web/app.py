from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import chess.engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from blunder_tutor.analysis.db import ensure_schema
from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob
from blunder_tutor.background.jobs.sync_games import SyncGamesJob
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService
from blunder_tutor.web import routes
from blunder_tutor.web.config import AppConfig, config_factory
from blunder_tutor.web.middleware import SetupCheckMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context manager for FastAPI app startup/shutdown."""
    config: AppConfig = app.state.config

    # Startup: create async engine
    transport, engine = await chess.engine.popen_uci(config.engine_path)
    app.state.transport = transport
    app.state.engine = engine

    # Set event loop on job service for cross-thread event publishing
    loop = asyncio.get_running_loop()
    app.state.job_service.set_event_loop(loop)

    # Start scheduler in async context
    app.state.scheduler.start(app.state.scheduler_settings)

    # Start WebSocket broadcasting task
    asyncio.create_task(app.state.connection_manager.start_broadcasting())

    yield

    # Shutdown
    app.state.scheduler.shutdown()
    await app.state.engine.quit()


def create_app(
    config: AppConfig,
) -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    ensure_schema(config.data.db_path)

    settings = SettingsRepository.from_config(config=config)

    templates = Jinja2Templates(directory=str(config.data.template_dir))

    limit = (
        chess.engine.Limit(time=config.engine.time_limit)
        if config.engine.time_limit is not None
        else chess.engine.Limit(depth=config.depth)
    )
    app.state.config = config
    app.state.templates = templates
    app.state.limit = limit

    # Initialize event bus and WebSocket manager
    event_bus = EventBus()
    app.state.event_bus = event_bus

    connection_manager = ConnectionManager(event_bus)
    app.state.connection_manager = connection_manager

    # Initialize background scheduler (but don't start yet)
    scheduler = BackgroundScheduler(config.data.db_path)
    app.state.scheduler = scheduler
    app.state.scheduler_settings = settings.get_all_settings()

    # Create job dependencies for scheduler
    job_repo = JobRepository(db_path=config.data.db_path)
    job_service = JobService(job_repository=job_repo, event_bus=event_bus)
    game_repo = GameRepository(db_path=config.data.db_path)
    analysis_repo = AnalysisRepository(db_path=config.data.db_path)

    # Create job instances for scheduler
    analyze_job = AnalyzeGamesJob(
        job_service=job_service,
        game_repo=game_repo,
        analysis_repo=analysis_repo,
    )
    sync_job = SyncGamesJob(
        job_service=job_service,
        settings_repo=settings,
        game_repo=game_repo,
        analyze_job=analyze_job,
    )

    # Configure scheduler with sync job
    scheduler.configure_sync_job(sync_job)

    # Store job_service for event loop setup
    app.state.job_service = job_service

    # Mount static files directory
    static_dir = Path(__file__).parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Add setup check middleware
    app.add_middleware(SetupCheckMiddleware)
    app = routes.configure_router(app)
    return app


def create_app_factory() -> FastAPI:
    """Factory function for uvicorn --factory mode."""
    return create_app(config_factory(None, os.environ))
