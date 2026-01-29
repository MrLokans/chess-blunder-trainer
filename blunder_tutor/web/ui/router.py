from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from blunder_tutor.web.dependencies import SettingsRepoDep


async def home(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "trainer.html",
        {"request": request, "title": "Blunder Trainer"},
    )


async def dashboard(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": "Dashboard"},
    )


async def management(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "management.html",
        {"request": request, "title": "Management"},
    )


async def settings(request: Request, settings_repo: SettingsRepoDep) -> HTMLResponse:
    usernames = await settings_repo.get_configured_usernames()

    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "lichess_username": usernames.get("lichess"),
            "chesscom_username": usernames.get("chesscom"),
        },
    )


async def setup(request: Request, settings_repo: SettingsRepoDep) -> HTMLResponse:
    if await settings_repo.is_setup_completed():
        return RedirectResponse(url="/", status_code=303)

    return request.app.state.templates.TemplateResponse(
        "setup.html",
        {"request": request},
    )


ui_router = APIRouter()
ui_router.add_api_route("/", home, response_class=HTMLResponse, methods=["GET"])
ui_router.add_api_route(
    "/dashboard", dashboard, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/management", management, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route("/setup", setup, response_class=HTMLResponse, methods=["GET"])
ui_router.add_api_route(
    "/settings", settings, response_class=HTMLResponse, methods=["GET"]
)
