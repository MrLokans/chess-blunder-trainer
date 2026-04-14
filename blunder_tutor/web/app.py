from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import chess.engine
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.background.executor import JobExecutor
from blunder_tutor.background.scheduler import BackgroundScheduler
from blunder_tutor.cache import (
    CacheInvalidator,
    InMemoryCacheBackend,
    NullCacheBackend,
)
from blunder_tutor.cache.decorator import set_cache_backend
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.websocket_manager import ConnectionManager
from blunder_tutor.i18n import TranslationManager
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.web import routes
from blunder_tutor.web.config import AppConfig, config_factory
from blunder_tutor.web.middleware import (
    DemoModeMiddleware,
    LocaleMiddleware,
    SetupCheckMiddleware,
)
from blunder_tutor.web.throttle import create_engine_throttle
from blunder_tutor.web.vite import vite_asset


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Async lifespan context manager for FastAPI app startup/shutdown."""

    # Startup: create work coordinator with engine pool
    coordinator: WorkCoordinator = app.state.work_coordinator
    await coordinator.start()

    # Load settings asynchronously
    settings_repo = app.state.settings_repo
    scheduler_settings = await settings_repo.get_all_settings()

    # Seed locale cache from DB so templates render the saved language
    # without relying on a cookie being present
    saved_locale = scheduler_settings.get("locale")
    if saved_locale:
        app.state._locale_cache = saved_locale

    # Start scheduler in async context
    app.state.scheduler.start(scheduler_settings)

    # Start WebSocket broadcasting task
    asyncio.create_task(app.state.connection_manager.start_broadcasting())

    # Start JobExecutor to handle job execution requests
    asyncio.create_task(app.state.job_executor.start())
    asyncio.create_task(app.state.cache_invalidator.start())

    yield

    # Shutdown
    await app.state.cache_invalidator.stop()
    await app.state.job_executor.shutdown()
    app.state.scheduler.shutdown()
    await coordinator.shutdown()
    await settings_repo.close()


def create_app(
    config: AppConfig,
) -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    run_migrations(config.data.db_path)

    settings = SettingsRepository.from_config(config=config)

    templates = Jinja2Templates(directory=str(config.data.template_dir))

    # Initialize i18n
    locales_dir = Path(__file__).parent.parent.parent / "locales"
    i18n = TranslationManager(locales_dir)
    app.state.i18n = i18n

    # Register Jinja2 global for translations
    templates.env.globals["t"] = (
        lambda key, **kwargs: key
    )  # placeholder, overridden per-request
    templates.env.globals["available_locales"] = i18n.available_locales
    templates.env.globals["vite_asset"] = lambda entry: vite_asset(
        entry, dev_mode=config.vite_dev
    )

    limit = (
        chess.engine.Limit(time=config.engine.time_limit)
        if config.engine.time_limit is not None
        else chess.engine.Limit(depth=config.engine.depth)
    )
    app.state.config = config
    app.state.templates = templates
    app.state.limit = limit

    # Initialize work coordinator (engine pool + task queue)
    work_coordinator = WorkCoordinator(engine_path=config.engine_path)
    app.state.work_coordinator = work_coordinator

    # Initialize event bus and WebSocket manager
    event_bus = EventBus()
    app.state.event_bus = event_bus

    if config.cache.enabled:
        cache_backend = InMemoryCacheBackend()
    else:
        cache_backend = NullCacheBackend()
    app.state.cache = cache_backend
    set_cache_backend(cache_backend, default_ttl=config.cache.default_ttl)

    cache_invalidator = CacheInvalidator(cache=cache_backend, event_bus=event_bus)
    app.state.cache_invalidator = cache_invalidator

    connection_manager = ConnectionManager(event_bus)
    app.state.connection_manager = connection_manager

    # Initialize JobExecutor for handling job execution requests
    job_executor = JobExecutor(
        event_bus=event_bus,
        db_path=config.data.db_path,
        engine_path=config.engine_path,
        work_coordinator=work_coordinator,
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

    # Inject demo_mode flag into app state and templates
    app.state.demo_mode = config.demo_mode
    templates.env.globals["demo_mode"] = config.demo_mode

    # Inject analytics config into templates
    templates.env.globals["analytics_enabled"] = config.analytics.enabled
    templates.env.globals["plausible_domain"] = config.analytics.plausible_domain
    templates.env.globals["plausible_script_url"] = (
        config.analytics.plausible_script_url
    )

    # Set up per-IP engine throttle for demo mode
    app.state.engine_throttle = create_engine_throttle(config)

    # Add middleware (order matters: last added = first executed)
    app.add_middleware(SetupCheckMiddleware)
    app.add_middleware(DemoModeMiddleware)
    app.add_middleware(LocaleMiddleware)
    app = routes.configure_router(app)
    return app


def create_app_factory() -> FastAPI:
    """Factory function for uvicorn --factory mode."""
    return create_app(config_factory(None, os.environ))
