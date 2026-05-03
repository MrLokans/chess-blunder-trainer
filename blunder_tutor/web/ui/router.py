from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from blunder_tutor.features import FEATURE_GROUPS, FEATURE_LABELS
from blunder_tutor.web.template_context import LOCALE_DISPLAY_NAMES


def _page(
    request: Request, template: str, title: str | None = None, **extra
) -> HTMLResponse:
    context: dict[str, object] = dict(extra)
    if title is not None:
        context["title"] = title
    return request.app.state.templates.TemplateResponse(request, template, context)


async def home(request: Request) -> HTMLResponse:
    return _page(request, "trainer.html", "Blunder Trainer")


async def dashboard(request: Request) -> HTMLResponse:
    return _page(request, "dashboard.html", "Dashboard")


async def management(request: Request) -> HTMLResponse:
    return _page(request, "management.html", "Management")


async def settings(request: Request) -> HTMLResponse:
    feature_groups_tuples = [
        (group_label, [(f.value, FEATURE_LABELS[f]) for f in group_features])
        for group_label, group_features in FEATURE_GROUPS
    ]

    features: dict[str, bool] = getattr(request.state, "features", {})
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

    i18n = request.app.state.i18n
    available_locales_data = [
        {"code": code, "name": LOCALE_DISPLAY_NAMES.get(code, code)}
        for code in i18n.available_locales()
    ]

    current_locale = getattr(request.state, "locale", "en")

    return _page(
        request,
        "settings.html",
        feature_groups_data=feature_groups_data,
        available_locales_data=available_locales_data,
        current_locale=current_locale,
    )


async def traps_page(request: Request) -> HTMLResponse:
    return _page(request, "traps.html", "Traps & Attacks")


async def import_page(request: Request) -> HTMLResponse:
    return _page(request, "import.html", "Import PGN")


async def game_review_page(request: Request, game_id: str) -> HTMLResponse:
    return _page(request, "game_review.html", "Game Review", game_id=game_id)


async def starred_page(request: Request) -> HTMLResponse:
    return _page(request, "starred.html", "Starred Puzzles")


async def profiles_page(request: Request) -> HTMLResponse:
    return _page(request, "profiles.html", "Profiles")


_GET = frozenset(("GET",))

ui_router = APIRouter()
ui_router.add_api_route("/", home, response_class=HTMLResponse, methods=_GET)
ui_router.add_api_route(
    "/dashboard", dashboard, response_class=HTMLResponse, methods=_GET
)
ui_router.add_api_route(
    "/management", management, response_class=HTMLResponse, methods=_GET
)
ui_router.add_api_route("/traps", traps_page, response_class=HTMLResponse, methods=_GET)
ui_router.add_api_route(
    "/import", import_page, response_class=HTMLResponse, methods=_GET
)
ui_router.add_api_route(
    "/starred", starred_page, response_class=HTMLResponse, methods=_GET
)
ui_router.add_api_route(
    "/game/{game_id}", game_review_page, response_class=HTMLResponse, methods=_GET
)
ui_router.add_api_route(
    "/settings", settings, response_class=HTMLResponse, methods=_GET
)
ui_router.add_api_route(
    "/profiles", profiles_page, response_class=HTMLResponse, methods=_GET
)
