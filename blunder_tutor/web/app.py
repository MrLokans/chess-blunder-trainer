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
from blunder_tutor.background.executor import JobExecutor
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.repositories.settings import SettingsRepository
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

    # Load scheduler settings asynchronously
    settings_repo = app.state.settings_repo
    scheduler_settings = await settings_repo.get_all_settings()

    # Start scheduler in async context
    app.state.scheduler.start(scheduler_settings)

    # Start WebSocket broadcasting task
    asyncio.create_task(app.state.connection_manager.start_broadcasting())

    # Start JobExecutor to handle job execution requests
    asyncio.create_task(app.state.job_executor.start())

    yield

    # Shutdown
    await app.state.job_executor.shutdown()
    app.state.scheduler.shutdown()
    await app.state.engine.quit()
    await settings_repo.close()


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

    # Initialize JobExecutor for handling job execution requests
    job_executor = JobExecutor(
        event_bus=event_bus,
        db_path=config.data.db_path,
        engine_path=config.engine_path,
    )
    app.state.job_executor = job_executor

    # Initialize background scheduler (but don't start yet)
    scheduler = BackgroundScheduler(
        db_path=config.data.db_path,
        event_bus=event_bus,
        engine_path=config.engine_path,
    )
    app.state.scheduler = scheduler
    app.state.settings_repo = settings

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
