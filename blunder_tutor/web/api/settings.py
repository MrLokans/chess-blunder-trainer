from __future__ import annotations

from collections.abc import Callable, Mapping
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter

from blunder_tutor.auth.fastapi import UserContextDep
from blunder_tutor.constants import (
    JOB_STATUS_NO_JOBS,
    JOB_STATUS_RUNNING,
    JOB_TYPE_DELETE_ALL_DATA,
)
from blunder_tutor.events.event_types import JobExecutionRequestEvent
from blunder_tutor.web.api import _settings_schemas as schemas
from blunder_tutor.web.api.schemas import SuccessResponse
from blunder_tutor.web.dependencies import (
    EventBusDep,
    JobServiceDep,
    SettingsRepoDep,
)
from blunder_tutor.web.request_helpers import _cache_key

if TYPE_CHECKING:
    from blunder_tutor.repositories.settings import SettingsRepository

_SECONDS_PER_HOUR = 3600
_HOURS_PER_DAY = 24
_DAYS_PER_YEAR = 365
LOCALE_COOKIE_MAX_AGE_SECONDS = _DAYS_PER_YEAR * _HOURS_PER_DAY * _SECONDS_PER_HOUR

settings_router = APIRouter()


@settings_router.post(
    "/api/setup/complete",
    response_model=SuccessResponse,
    summary="Mark initial setup as complete",
    description=(
        "Idempotent flag flip. Called by the rewritten SetupApp once profiles "
        "have been created and import jobs dispatched, so the SetupCheck "
        "middleware stops redirecting to /setup."
    ),
)
async def setup_complete(
    request: Request,
    settings_repo: SettingsRepoDep,
) -> dict[str, bool]:
    await settings_repo.mark_setup_completed()
    request.app.state.setup_completed_cache.invalidate(_cache_key(request))
    return {"success": True}


@settings_router.get(
    "/api/settings",
    response_model=schemas.SettingsResponse,
    summary="Get all settings",
    description="Retrieve all application settings including usernames, sync config, and training preferences.",
)
async def get_settings(settings_repo: SettingsRepoDep) -> dict[str, Any]:
    settings = await settings_repo.get_all_settings()

    return {
        "lichess_username": settings.get("lichess_username"),
        "chesscom_username": settings.get("chesscom_username"),
        "auto_sync": settings.get("auto_sync_enabled") == "true",
        "sync_interval": int(settings.get("sync_interval_hours", "24")),
        "max_games": int(settings.get("sync_max_games", "100")),
        "auto_analyze": settings.get("analyze_new_games_automatically", "true")
        == "true",
        "spaced_repetition_days": int(settings.get("spaced_repetition_days", "30")),
    }


@settings_router.get(
    "/api/settings/theme/presets",
    response_model=schemas.ThemePresetsResponse,
    summary="Get available theme presets",
    description="Returns a list of predefined theme presets.",
)
async def get_theme_presets() -> dict[str, Any]:
    presets = [
        {
            "id": preset_id,
            "name": data["name"],
            "description": data["description"],
            "colors": data["colors"],
        }
        for preset_id, data in schemas.THEME_PRESETS.items()
    ]
    return {"presets": presets}


@settings_router.get(
    "/api/settings/board/piece-sets",
    response_model=schemas.PieceSetsResponse,
    summary="Get available piece sets",
    description="Returns a list of available chess piece sets.",
)
async def get_piece_sets() -> dict[str, Any]:
    return {"piece_sets": schemas.PIECE_SETS}


@settings_router.get(
    "/api/settings/board/color-presets",
    response_model=schemas.BoardColorPresetsResponse,
    summary="Get board color presets",
    description="Returns a list of predefined board color combinations.",
)
async def get_board_color_presets() -> dict[str, Any]:
    presets = [
        {"id": preset_id, **data}
        for preset_id, data in schemas.BOARD_COLOR_PRESETS.items()
    ]
    return {"presets": presets}


@settings_router.get(
    "/api/settings/board",
    response_model=schemas.BoardSettingsResponse,
    summary="Get board settings",
    description="Retrieve current board styling settings.",
)
async def get_board_settings(settings_repo: SettingsRepoDep) -> dict[str, str]:
    piece_set = await settings_repo.read_setting("board_piece_set")
    board_light = await settings_repo.read_setting("board_light_color")
    board_dark = await settings_repo.read_setting("board_dark_color")

    return {
        "piece_set": piece_set or schemas.DEFAULT_PIECE_SET,
        "board_light": board_light or schemas.DEFAULT_BOARD_LIGHT,
        "board_dark": board_dark or schemas.DEFAULT_BOARD_DARK,
    }


def _validate_piece_set(value: str) -> None:
    valid_sets = {ps["id"] for ps in schemas.PIECE_SETS}
    if value not in valid_sets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid piece set. Valid options: {', '.join(valid_sets)}",
        )


def _validate_hex_color(field: str, value: str) -> None:
    if not value.startswith("#") or len(value) != 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} must be a valid hex color (#RRGGBB)",
        )


type _BoardFieldSpec = tuple[Callable[[str], None], str]

# Per-field (validator, db_key) for board settings. Keeps the endpoint a
# straight loop instead of nested if-blocks.
_BOARD_FIELDS: Mapping[str, _BoardFieldSpec] = MappingProxyType(
    {
        "piece_set": (_validate_piece_set, "board_piece_set"),
        "board_light": (
            lambda v: _validate_hex_color("board_light", v),
            "board_light_color",
        ),
        "board_dark": (
            lambda v: _validate_hex_color("board_dark", v),
            "board_dark_color",
        ),
    }
)


@settings_router.post(
    "/api/settings/board",
    response_model=SuccessResponse,
    summary="Update board settings",
    description="Update board styling settings (piece set, board colors).",
)
async def update_board_settings(
    payload: schemas.BoardSettingsRequest, settings_repo: SettingsRepoDep
) -> dict[str, bool]:
    payload_dict = payload.model_dump()
    for field, (validate, db_key) in _BOARD_FIELDS.items():
        value = payload_dict.get(field)
        if value is None:
            continue
        validate(value)
        await settings_repo.write_setting(db_key, value)
    return {"success": True}


@settings_router.post(
    "/api/settings/board/reset",
    response_model=SuccessResponse,
    summary="Reset board settings",
    description="Reset board styling to defaults.",
)
async def reset_board_settings(settings_repo: SettingsRepoDep) -> dict[str, bool]:
    await settings_repo.write_setting("board_piece_set", None)
    await settings_repo.write_setting("board_light_color", None)
    await settings_repo.write_setting("board_dark_color", None)
    return {"success": True}


@settings_router.get(
    "/api/settings/theme",
    response_model=schemas.ThemeColors,
    summary="Get theme colors",
    description="Retrieve the current theme color settings.",
)
async def get_theme(settings_repo: SettingsRepoDep) -> dict[str, str]:
    result: dict[str, str] = {}
    for key in schemas.THEME_KEYS:
        value = await settings_repo.read_setting(f"theme_{key}")
        result[key] = value or schemas.DEFAULT_THEME[key]
    return result


@settings_router.post(
    "/api/settings/theme/reset",
    response_model=SuccessResponse,
    summary="Reset theme to defaults",
    description="Reset all theme colors to their default values.",
)
async def reset_theme(settings_repo: SettingsRepoDep) -> dict[str, bool]:
    for key in schemas.THEME_KEYS:
        await settings_repo.write_setting(f"theme_{key}", None)
    return {"success": True}


async def _persist_theme(
    settings_repo: SettingsRepository, theme: schemas.ThemeColors
) -> None:
    for key, value in theme.model_dump().items():
        await settings_repo.write_setting(f"theme_{key}", value)


async def _persist_general_settings(
    settings_repo: SettingsRepository, payload: schemas.SettingsRequest
) -> None:
    await settings_repo.write_setting(
        "auto_sync_enabled", "true" if payload.auto_sync else "false"
    )
    await settings_repo.write_setting("sync_interval_hours", str(payload.sync_interval))
    await settings_repo.write_setting("sync_max_games", str(payload.max_games))
    await settings_repo.write_setting(
        "analyze_new_games_automatically", "true" if payload.auto_analyze else "false"
    )
    await settings_repo.write_setting(
        "spaced_repetition_days", str(payload.spaced_repetition_days)
    )


@settings_router.post(
    "/api/settings",
    response_model=SuccessResponse,
    summary="Update settings",
    description="Update application settings including sync configuration and analysis preferences.",
)
async def settings_submit(
    payload: schemas.SettingsRequest,
    settings_repo: SettingsRepoDep,
) -> dict[str, bool]:
    await _persist_general_settings(settings_repo, payload)
    if payload.theme:
        await _persist_theme(settings_repo, payload.theme)
    # No scheduler hot-reload: BackgroundScheduler reads settings on each
    # fanout tick, so changes take effect within ``DEFAULT_TICK_SECONDS``.
    return {"success": True}


@settings_router.get(
    "/api/settings/features",
    response_model=schemas.FeatureFlagsResponse,
    summary="Get feature visibility flags",
    description="Retrieve current feature visibility settings.",
)
async def get_features(settings_repo: SettingsRepoDep) -> dict[str, Any]:
    features = await settings_repo.read_feature_flags()
    return {"features": features}


@settings_router.post(
    "/api/settings/features",
    response_model=SuccessResponse,
    summary="Update feature visibility flags",
    description="Toggle visibility of individual features.",
)
async def update_features(
    request: Request,
    payload: schemas.FeatureFlagsRequest,
    settings_repo: SettingsRepoDep,
) -> dict[str, bool]:
    await settings_repo.write_feature_flags(payload.features)
    request.app.state.features_cache.invalidate(_cache_key(request))
    return {"success": True}


@settings_router.post(
    "/api/settings/locale",
    response_model=SuccessResponse,
    summary="Set display locale",
    description="Update the application display language.",
)
async def set_locale(
    request: Request, payload: schemas.LocaleRequest, settings_repo: SettingsRepoDep
) -> JSONResponse:
    i18n = getattr(request.app.state, "i18n", None)
    if i18n and payload.locale not in i18n.available_locales():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported locale"
        )
    await settings_repo.write_setting("locale", payload.locale)
    request.app.state.locale_cache.set(_cache_key(request), payload.locale)

    response = JSONResponse(content={"success": True})
    response.set_cookie(
        key="locale",
        value=payload.locale,
        path="/",
        max_age=LOCALE_COOKIE_MAX_AGE_SECONDS,
        samesite="lax",
    )
    return response


@settings_router.delete(
    "/api/data/all",
    response_model=schemas.DeleteAllResponse,
    summary="Delete all data",
    description="Start a background job to delete all imported games, analysis results, puzzle attempts, and job history. Settings are preserved.",
)
async def delete_all_data(
    job_service: JobServiceDep,
    event_bus: EventBusDep,
    user_ctx: UserContextDep,
) -> dict[str, Any]:
    job_id = await job_service.create_job(job_type=JOB_TYPE_DELETE_ALL_DATA)

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type=JOB_TYPE_DELETE_ALL_DATA,
        user_id=user_ctx.user_id,
    )
    await event_bus.publish(event)

    return {"job_id": job_id}


@settings_router.get(
    "/api/data/delete-status",
    summary="Get delete all status",
    description="Get the status of the most recent or currently running delete all job.",
)
async def get_delete_all_status(job_service: JobServiceDep) -> dict[str, Any]:
    running_jobs = await job_service.list_jobs(
        job_type=JOB_TYPE_DELETE_ALL_DATA, status=JOB_STATUS_RUNNING, limit=1
    )

    if running_jobs:
        return running_jobs[0]

    recent_jobs = await job_service.list_jobs(
        job_type=JOB_TYPE_DELETE_ALL_DATA, limit=1
    )

    if not recent_jobs:
        return {"status": JOB_STATUS_NO_JOBS}

    return recent_jobs[0]
