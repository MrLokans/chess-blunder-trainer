from __future__ import annotations

import asyncio
import os
from pathlib import Path

import chess.engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from blunder_tutor.analysis.db import ensure_schema
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web import routes
from blunder_tutor.web.config import AppConfig, config_factory
from blunder_tutor.web.middleware import SetupCheckMiddleware


def create_app(
    config: AppConfig,
) -> FastAPI:
    app = FastAPI()

    ensure_schema(config.data.db_path)

    settings = SettingsRepository.from_config(config=config)

    templates = Jinja2Templates(directory=str(config.data.template_dir))

    engine = chess.engine.SimpleEngine.popen_uci(config.engine_path)
    limit = (
        chess.engine.Limit(time=config.engine.time_limit)
        if config.engine.time_limit is not None
        else chess.engine.Limit(depth=config.depth)
    )
    app.state.config = config
    app.state.templates = templates
    app.state.engine = engine
    app.state.limit = limit

    # Initialize background scheduler (but don't start yet)
    scheduler = BackgroundScheduler(config.data.data_dir, config.data.db_path)
    app.state.scheduler = scheduler
    app.state.scheduler_settings = settings.get_all_settings()

    # Initialize event bus and WebSocket manager
    event_bus = EventBus()
    app.state.event_bus = event_bus

    connection_manager = ConnectionManager(event_bus)
    app.state.connection_manager = connection_manager

    @app.on_event("startup")
    async def _startup() -> None:
        # Start scheduler in async context
        scheduler.start(app.state.scheduler_settings, event_bus)

        # Start WebSocket broadcasting task
        asyncio.create_task(connection_manager.start_broadcasting())

    @app.on_event("shutdown")
    def _shutdown() -> None:
        scheduler.shutdown()
        engine.quit()

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
