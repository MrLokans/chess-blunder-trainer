from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from blunder_tutor.features import FEATURE_GROUPS, FEATURE_LABELS


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


async def settings(request: Request) -> HTMLResponse:
    feature_groups_tuples = [
        (group_label, [(f.value, FEATURE_LABELS[f]) for f in group_features])
        for group_label, group_features in FEATURE_GROUPS
    ]

    features = request.app.state.templates.env.globals.get("features", {})
    feature_groups_data = [
        {
            "label": group_label,
            "features": [
                {
                    "id": fid,
                    "label": label_key,
                    "enabled": features.get(fid, True),
                }
                for fid, label_key in group_features
            ],
        }
        for group_label, group_features in feature_groups_tuples
    ]

    locale_display_names = request.app.state.templates.env.globals.get(
        "locale_display_names", {}
    )
    available_locales_fn = request.app.state.templates.env.globals.get(
        "available_locales", lambda: []
    )
    available_locales_data = [
        {"code": code, "name": locale_display_names.get(code, code)}
        for code in available_locales_fn()
    ]

    current_locale = request.app.state.templates.env.globals.get("locale", "en")

    return request.app.state.templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "feature_groups_data": feature_groups_data,
            "available_locales_data": available_locales_data,
            "current_locale": current_locale,
        },
    )


async def traps_page(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "traps.html",
        {"request": request, "title": "Traps & Attacks"},
    )


async def import_page(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "import.html",
        {"request": request, "title": "Import PGN"},
    )


async def game_review_page(request: Request, game_id: str) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "game_review.html",
        {"request": request, "title": "Game Review", "game_id": game_id},
    )


async def starred_page(request: Request) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        "starred.html",
        {"request": request, "title": "Starred Puzzles"},
    )


ui_router = APIRouter()
ui_router.add_api_route("/", home, response_class=HTMLResponse, methods=["GET"])
ui_router.add_api_route(
    "/dashboard", dashboard, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/management", management, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/traps", traps_page, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/import", import_page, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/starred", starred_page, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/game/{game_id}", game_review_page, response_class=HTMLResponse, methods=["GET"]
)
ui_router.add_api_route(
    "/settings", settings, response_class=HTMLResponse, methods=["GET"]
)
