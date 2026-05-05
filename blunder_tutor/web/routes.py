from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from blunder_tutor.web.api import websocket
from blunder_tutor.web.api.analysis import analysis_router
from blunder_tutor.web.api.auth import router as auth_router
from blunder_tutor.web.api.debug import debug_router
from blunder_tutor.web.api.game_review import game_review_router
from blunder_tutor.web.api.import_game import import_router
from blunder_tutor.web.api.jobs import jobs_router
from blunder_tutor.web.api.profiles import profiles_router
from blunder_tutor.web.api.rating_history import rating_history_router
from blunder_tutor.web.api.settings import settings_router
from blunder_tutor.web.api.starred import starred_router
from blunder_tutor.web.api.stats import stats_router
from blunder_tutor.web.api.system import system_router
from blunder_tutor.web.api.traps import traps_router
from blunder_tutor.web.ui.auth import auth_ui_router
from blunder_tutor.web.ui.router import ui_router


def health_check(request: Request) -> JSONResponse:
    return JSONResponse({"status": "healthy"})


def configure_router(app: FastAPI) -> FastAPI:
    router = APIRouter()

    # Health check
    router.add_api_route(
        "/health", health_check, response_class=JSONResponse, methods=["GET"]
    )

    app.include_router(router)
    app.include_router(auth_router)
    app.include_router(auth_ui_router)
    app.include_router(ui_router)
    app.include_router(settings_router)
    app.include_router(jobs_router)
    app.include_router(stats_router)
    app.include_router(analysis_router)
    app.include_router(system_router)
    app.include_router(traps_router)
    app.include_router(debug_router)
    app.include_router(game_review_router)
    app.include_router(import_router)
    app.include_router(starred_router)
    app.include_router(profiles_router)
    app.include_router(rating_history_router)
    app.include_router(websocket.router)
    return app
