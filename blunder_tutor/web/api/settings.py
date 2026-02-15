from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from blunder_tutor.events import JobExecutionRequestEvent
from blunder_tutor.fetchers.validation import validate_username
from blunder_tutor.web.api.schemas import ErrorResponse, SuccessResponse
from blunder_tutor.web.dependencies import EventBusDep, JobServiceDep, SettingsRepoDep


class ValidateUsernameRequest(BaseModel):
    platform: str = Field(description="Platform: 'lichess' or 'chesscom'")
    username: str = Field(description="Username to validate")


class ValidateUsernameResponse(BaseModel):
    valid: bool = Field(description="Whether the username exists on the platform")
    platform: str = Field(description="Platform that was checked")
    username: str = Field(description="Username that was checked")


class SetupRequest(BaseModel):
    lichess: str = Field(default="", description="Lichess username")
    chesscom: str = Field(
        default="", description="Chess.com username (with or without alias)"
    )


class ThemeColors(BaseModel):
    # Core accent colors
    primary: str = Field(default="#4f6d7a", description="Primary accent color")
    success: str = Field(default="#3d8b6e", description="Success/positive color")
    error: str = Field(default="#c25450", description="Error/danger color")
    warning: str = Field(default="#b8860b", description="Warning color")
    # Game phase colors
    phase_opening: str = Field(default="#5b8a9a", description="Opening phase color")
    phase_middlegame: str = Field(
        default="#9a7b5b", description="Middlegame phase color"
    )
    phase_endgame: str = Field(default="#7a5b9a", description="Endgame phase color")
    # Background colors
    bg: str = Field(default="#f1f5f9", description="Page background color")
    bg_card: str = Field(default="#ffffff", description="Card background color")
    # Text colors
    text: str = Field(default="#1e293b", description="Primary text color")
    text_muted: str = Field(default="#64748b", description="Muted/secondary text color")
    # Heatmap colors (GitHub-style activity levels)
    heatmap_empty: str = Field(default="#ebedf0", description="Heatmap empty cell")
    heatmap_l1: str = Field(default="#9be9a8", description="Heatmap level 1 (low)")
    heatmap_l2: str = Field(default="#40c463", description="Heatmap level 2")
    heatmap_l3: str = Field(default="#30a14e", description="Heatmap level 3")
    heatmap_l4: str = Field(default="#216e39", description="Heatmap level 4 (high)")


class SettingsRequest(BaseModel):
    auto_sync: bool = Field(default=False, description="Enable automatic game sync")
    sync_interval: int = Field(
        default=24, ge=1, le=168, description="Sync interval in hours"
    )
    max_games: int = Field(
        default=100, ge=1, le=10000, description="Maximum games to sync"
    )
    auto_analyze: bool = Field(
        default=True, description="Automatically analyze new games"
    )
    spaced_repetition_days: int = Field(
        default=30, ge=1, le=365, description="Days before repeating solved puzzles"
    )
    theme: ThemeColors | None = Field(default=None, description="Theme color settings")


class UsernamesResponse(BaseModel):
    lichess_username: str | None = Field(
        None, description="Configured Lichess username"
    )
    chesscom_username: str | None = Field(
        None, description="Configured Chess.com username"
    )


class SettingsResponse(BaseModel):
    lichess_username: str | None = Field(None, description="Lichess username")
    chesscom_username: str | None = Field(None, description="Chess.com username")
    auto_sync: bool = Field(default=False, description="Auto sync enabled")
    sync_interval: int = Field(default=24, description="Sync interval in hours")
    max_games: int = Field(default=100, description="Max games to sync")
    auto_analyze: bool = Field(default=True, description="Auto analyze new games")
    spaced_repetition_days: int = Field(
        default=30, description="Spaced repetition days"
    )


settings_router = APIRouter()


@settings_router.post(
    "/api/validate-username",
    response_model=ValidateUsernameResponse,
    summary="Validate chess platform username",
    description="Check whether a username exists on the specified chess platform.",
)
async def validate_username_endpoint(
    payload: ValidateUsernameRequest,
) -> dict[str, Any]:
    username = payload.username.strip()
    platform = payload.platform.strip().lower()

    if platform not in ("lichess", "chesscom"):
        raise HTTPException(
            status_code=400, detail="Platform must be 'lichess' or 'chesscom'"
        )

    if not username:
        raise HTTPException(status_code=400, detail="Username is required")

    valid = await validate_username(platform, username)
    return {"valid": valid, "platform": platform, "username": username}


class SetupResponse(BaseModel):
    success: bool = Field(description="Operation success status")
    import_job_ids: list[str] = Field(
        default_factory=list, description="Job IDs for triggered imports"
    )


@settings_router.post(
    "/api/setup",
    response_model=SetupResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least one username is required",
        }
    },
    summary="Complete initial setup",
    description="Configure usernames for Lichess and/or Chess.com accounts. Triggers background import.",
)
async def setup_submit(
    request: Request,
    payload: SetupRequest,
    settings_repo: SettingsRepoDep,
    job_service: JobServiceDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    lichess = payload.lichess.strip()
    chesscom = payload.chesscom.strip()

    if not lichess and not chesscom:
        raise HTTPException(
            status_code=400,
            detail="At least one username is required (Lichess or Chess.com)",
        )

    invalid_usernames: list[str] = []
    if lichess and not await validate_username("lichess", lichess):
        invalid_usernames.append(f"Lichess user '{lichess}' not found")
    if chesscom and not await validate_username("chesscom", chesscom):
        invalid_usernames.append(f"Chess.com user '{chesscom}' not found")

    if invalid_usernames:
        raise HTTPException(status_code=400, detail="; ".join(invalid_usernames))

    await settings_repo.set_setting("lichess_username", lichess if lichess else None)
    await settings_repo.set_setting("chesscom_username", chesscom if chesscom else None)
    await settings_repo.mark_setup_completed()

    if hasattr(request.app.state, "_setup_completed_cache"):
        delattr(request.app.state, "_setup_completed_cache")

    import_job_ids: list[str] = []
    max_games_str = await settings_repo.get_setting("sync_max_games")
    max_games = int(max_games_str) if max_games_str else 100

    for source, username in [("lichess", lichess), ("chesscom", chesscom)]:
        if not username:
            continue
        job_id = await job_service.create_job(
            job_type="import",
            username=username,
            source=source,
            max_games=max_games,
        )
        event = JobExecutionRequestEvent.create(
            job_id=job_id,
            job_type="import",
            source=source,
            username=username,
            max_games=max_games,
        )
        await event_bus.publish(event)
        import_job_ids.append(job_id)

    return {"success": True, "import_job_ids": import_job_ids}


@settings_router.get(
    "/api/settings/usernames",
    response_model=UsernamesResponse,
    summary="Get configured usernames",
    description="Retrieve the currently configured usernames for Lichess and Chess.com.",
)
async def get_usernames(settings_repo: SettingsRepoDep) -> dict[str, Any]:
    usernames = await settings_repo.get_configured_usernames()

    return {
        "lichess_username": usernames.get("lichess"),
        "chesscom_username": usernames.get("chesscom"),
    }


@settings_router.get(
    "/api/settings",
    response_model=SettingsResponse,
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


DEFAULT_THEME = {
    "primary": "#1A3A8F",
    "success": "#2D8F3E",
    "error": "#D42828",
    "warning": "#F2C12E",
    "phase_opening": "#1A3A8F",
    "phase_middlegame": "#F2C12E",
    "phase_endgame": "#3A3A3A",
    "bg": "#F5F2EB",
    "bg_card": "#F5F2EB",
    "text": "#1A1A1A",
    "text_muted": "#3A3A3A",
    "heatmap_empty": "#E8E4DB",
    "heatmap_l1": "#B8D9CA",
    "heatmap_l2": "#5BAA7D",
    "heatmap_l3": "#2D8F3E",
    "heatmap_l4": "#1A6B2A",
}

THEME_PRESETS = {
    "default": {
        "name": "Default",
        "description": "Muted slate tones for a calm, professional look",
        "colors": DEFAULT_THEME,
    },
    "ocean": {
        "name": "Ocean",
        "description": "Deep blue Bauhaus with cool undertones",
        "colors": {
            "primary": "#0B4F6C",
            "success": "#2A9D8F",
            "error": "#C43A31",
            "warning": "#E9C46A",
            "phase_opening": "#0B4F6C",
            "phase_middlegame": "#E9C46A",
            "phase_endgame": "#264653",
            "bg": "#EFF6F2",
            "bg_card": "#EFF6F2",
            "text": "#0A1628",
            "text_muted": "#3A5060",
            "heatmap_empty": "#D6E8E0",
            "heatmap_l1": "#7DD3C0",
            "heatmap_l2": "#2A9D8F",
            "heatmap_l3": "#1A7A6E",
            "heatmap_l4": "#0F5A52",
        },
    },
    "forest": {
        "name": "Forest",
        "description": "Earth tones with structural warmth",
        "colors": {
            "primary": "#2D6A4F",
            "success": "#40916C",
            "error": "#9B2226",
            "warning": "#BC6C25",
            "phase_opening": "#2D6A4F",
            "phase_middlegame": "#BC6C25",
            "phase_endgame": "#4A3728",
            "bg": "#F5F2ED",
            "bg_card": "#F5F2ED",
            "text": "#1B2E20",
            "text_muted": "#4A5E4A",
            "heatmap_empty": "#D8E8DC",
            "heatmap_l1": "#95D5B2",
            "heatmap_l2": "#52B788",
            "heatmap_l3": "#2D6A4F",
            "heatmap_l4": "#1B4332",
        },
    },
    "sunset": {
        "name": "Sunset",
        "description": "Warm reds and amber accents",
        "colors": {
            "primary": "#B83B1D",
            "success": "#2D8040",
            "error": "#8B1A1A",
            "warning": "#D4920A",
            "phase_opening": "#B83B1D",
            "phase_middlegame": "#D4920A",
            "phase_endgame": "#5C2E10",
            "bg": "#FBF5ED",
            "bg_card": "#FBF5ED",
            "text": "#2C1810",
            "text_muted": "#6B4E3A",
            "heatmap_empty": "#F5E6D0",
            "heatmap_l1": "#F0C888",
            "heatmap_l2": "#E0A050",
            "heatmap_l3": "#C07820",
            "heatmap_l4": "#8B5510",
        },
    },
    "lavender": {
        "name": "Lavender",
        "description": "Muted purples with geometric clarity",
        "colors": {
            "primary": "#5B2D8E",
            "success": "#2D7A50",
            "error": "#A82828",
            "warning": "#C4960A",
            "phase_opening": "#5B2D8E",
            "phase_middlegame": "#C4960A",
            "phase_endgame": "#3A2060",
            "bg": "#F5F2F8",
            "bg_card": "#F5F2F8",
            "text": "#1E1830",
            "text_muted": "#5A4E6A",
            "heatmap_empty": "#E8E0F0",
            "heatmap_l1": "#C4B0E0",
            "heatmap_l2": "#9A78C8",
            "heatmap_l3": "#5B2D8E",
            "heatmap_l4": "#3A1860",
        },
    },
    "monochrome": {
        "name": "Monochrome",
        "description": "Pure black and white, maximum structure",
        "colors": {
            "primary": "#1A1A1A",
            "success": "#3A3A3A",
            "error": "#1A1A1A",
            "warning": "#5A5A5A",
            "phase_opening": "#5A5A5A",
            "phase_middlegame": "#3A3A3A",
            "phase_endgame": "#1A1A1A",
            "bg": "#F0F0F0",
            "bg_card": "#F0F0F0",
            "text": "#0A0A0A",
            "text_muted": "#4A4A4A",
            "heatmap_empty": "#E0E0E0",
            "heatmap_l1": "#A0A0A0",
            "heatmap_l2": "#707070",
            "heatmap_l3": "#404040",
            "heatmap_l4": "#1A1A1A",
        },
    },
    "dark": {
        "name": "Dark",
        "description": "Inverted Bauhaus for low light",
        "colors": {
            "primary": "#5B8FD4",
            "success": "#4AAF6A",
            "error": "#E05050",
            "warning": "#F2C12E",
            "phase_opening": "#5B8FD4",
            "phase_middlegame": "#F2C12E",
            "phase_endgame": "#8A8A8A",
            "bg": "#1A1A1A",
            "bg_card": "#2A2A2A",
            "text": "#F0EDE6",
            "text_muted": "#8A8A80",
            "heatmap_empty": "#2A2A2A",
            "heatmap_l1": "#1A4A2A",
            "heatmap_l2": "#2A6A3A",
            "heatmap_l3": "#3A8A4A",
            "heatmap_l4": "#4AAF6A",
        },
    },
    "high_contrast": {
        "name": "High Contrast",
        "description": "Maximum readability with Bauhaus colors",
        "colors": {
            "primary": "#0000CC",
            "success": "#006B00",
            "error": "#CC0000",
            "warning": "#CC8800",
            "phase_opening": "#0000CC",
            "phase_middlegame": "#CC8800",
            "phase_endgame": "#333333",
            "bg": "#FFFFFF",
            "bg_card": "#FFFFFF",
            "text": "#000000",
            "text_muted": "#333333",
            "heatmap_empty": "#D0D0D0",
            "heatmap_l1": "#80CC80",
            "heatmap_l2": "#40AA40",
            "heatmap_l3": "#208020",
            "heatmap_l4": "#005500",
        },
    },
}

THEME_KEYS = list(DEFAULT_THEME.keys())

# Board styling constants
PIECE_SETS = [
    {"id": "alpha", "name": "Alpha", "format": "svg"},
    {"id": "california", "name": "California", "format": "svg"},
    {"id": "cardinal", "name": "Cardinal", "format": "svg"},
    {"id": "cburnett", "name": "CBurnett", "format": "svg"},
    {"id": "chessnut", "name": "Chessnut", "format": "svg"},
    {"id": "companion", "name": "Companion", "format": "svg"},
    {"id": "fresca", "name": "Fresca", "format": "svg"},
    {"id": "gioco", "name": "Gioco", "format": "svg"},
    {"id": "kosal", "name": "Kosal", "format": "svg"},
    {"id": "leipzig", "name": "Leipzig", "format": "svg"},
    {"id": "letter", "name": "Letter", "format": "svg"},
    {"id": "maestro", "name": "Maestro", "format": "svg"},
    {"id": "merida", "name": "Merida", "format": "svg"},
    {"id": "shapes", "name": "Shapes", "format": "svg"},
    {"id": "staunty", "name": "Staunty", "format": "svg"},
    {"id": "tatiana", "name": "Tatiana", "format": "svg"},
]

DEFAULT_PIECE_SET = "gioco"
DEFAULT_BOARD_LIGHT = "#E0E0E0"
DEFAULT_BOARD_DARK = "#A0A0A0"

BOARD_COLOR_PRESETS = {
    "brown": {
        "name": "Brown",
        "light": "#f0d9b5",
        "dark": "#b58863",
    },
    "blue": {
        "name": "Blue",
        "light": "#dee3e6",
        "dark": "#8ca2ad",
    },
    "green": {
        "name": "Green",
        "light": "#ffffdd",
        "dark": "#86a666",
    },
    "purple": {
        "name": "Purple",
        "light": "#e8e0f0",
        "dark": "#9070a0",
    },
    "gray": {
        "name": "Gray",
        "light": "#e0e0e0",
        "dark": "#a0a0a0",
    },
    "wood": {
        "name": "Wood",
        "light": "#e6d3ac",
        "dark": "#b88b4a",
    },
}


class ThemePreset(BaseModel):
    id: str = Field(description="Preset identifier")
    name: str = Field(description="Display name")
    description: str = Field(description="Short description")
    colors: ThemeColors = Field(description="Theme colors")


class ThemePresetsResponse(BaseModel):
    presets: list[ThemePreset] = Field(description="Available theme presets")


@settings_router.get(
    "/api/settings/theme/presets",
    response_model=ThemePresetsResponse,
    summary="Get available theme presets",
    description="Returns a list of predefined theme presets.",
)
async def get_theme_presets() -> dict[str, list[dict[str, Any]]]:
    presets = [
        {
            "id": preset_id,
            "name": data["name"],
            "description": data["description"],
            "colors": data["colors"],
        }
        for preset_id, data in THEME_PRESETS.items()
    ]
    return {"presets": presets}


# Board styling models
class PieceSetInfo(BaseModel):
    id: str = Field(description="Piece set identifier")
    name: str = Field(description="Display name")
    format: str = Field(description="Image format (png or svg)")


class BoardColorPreset(BaseModel):
    id: str = Field(description="Preset identifier")
    name: str = Field(description="Display name")
    light: str = Field(description="Light square color")
    dark: str = Field(description="Dark square color")


class BoardSettingsResponse(BaseModel):
    piece_set: str = Field(description="Current piece set ID")
    board_light: str = Field(description="Light square color")
    board_dark: str = Field(description="Dark square color")


class BoardSettingsRequest(BaseModel):
    piece_set: str | None = Field(default=None, description="Piece set ID")
    board_light: str | None = Field(default=None, description="Light square color")
    board_dark: str | None = Field(default=None, description="Dark square color")


class PieceSetsResponse(BaseModel):
    piece_sets: list[PieceSetInfo] = Field(description="Available piece sets")


class BoardColorPresetsResponse(BaseModel):
    presets: list[BoardColorPreset] = Field(description="Available board color presets")


@settings_router.get(
    "/api/settings/board/piece-sets",
    response_model=PieceSetsResponse,
    summary="Get available piece sets",
    description="Returns a list of available chess piece sets.",
)
async def get_piece_sets() -> dict[str, list[dict[str, str]]]:
    return {"piece_sets": PIECE_SETS}


@settings_router.get(
    "/api/settings/board/color-presets",
    response_model=BoardColorPresetsResponse,
    summary="Get board color presets",
    description="Returns a list of predefined board color combinations.",
)
async def get_board_color_presets() -> dict[str, list[dict[str, str]]]:
    presets = [
        {"id": preset_id, **data} for preset_id, data in BOARD_COLOR_PRESETS.items()
    ]
    return {"presets": presets}


@settings_router.get(
    "/api/settings/board",
    response_model=BoardSettingsResponse,
    summary="Get board settings",
    description="Retrieve current board styling settings.",
)
async def get_board_settings(settings_repo: SettingsRepoDep) -> dict[str, str]:
    piece_set = await settings_repo.get_setting("board_piece_set")
    board_light = await settings_repo.get_setting("board_light_color")
    board_dark = await settings_repo.get_setting("board_dark_color")

    return {
        "piece_set": piece_set or DEFAULT_PIECE_SET,
        "board_light": board_light or DEFAULT_BOARD_LIGHT,
        "board_dark": board_dark or DEFAULT_BOARD_DARK,
    }


@settings_router.post(
    "/api/settings/board",
    response_model=SuccessResponse,
    summary="Update board settings",
    description="Update board styling settings (piece set, board colors).",
)
async def update_board_settings(
    payload: BoardSettingsRequest, settings_repo: SettingsRepoDep
) -> dict[str, bool]:
    if payload.piece_set is not None:
        valid_sets = {ps["id"] for ps in PIECE_SETS}
        if payload.piece_set not in valid_sets:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid piece set. Valid options: {', '.join(valid_sets)}",
            )
        await settings_repo.set_setting("board_piece_set", payload.piece_set)

    if payload.board_light is not None:
        if not payload.board_light.startswith("#") or len(payload.board_light) != 7:
            raise HTTPException(
                status_code=400,
                detail="board_light must be a valid hex color (#RRGGBB)",
            )
        await settings_repo.set_setting("board_light_color", payload.board_light)

    if payload.board_dark is not None:
        if not payload.board_dark.startswith("#") or len(payload.board_dark) != 7:
            raise HTTPException(
                status_code=400, detail="board_dark must be a valid hex color (#RRGGBB)"
            )
        await settings_repo.set_setting("board_dark_color", payload.board_dark)

    return {"success": True}


@settings_router.post(
    "/api/settings/board/reset",
    response_model=SuccessResponse,
    summary="Reset board settings",
    description="Reset board styling to defaults.",
)
async def reset_board_settings(settings_repo: SettingsRepoDep) -> dict[str, bool]:
    await settings_repo.set_setting("board_piece_set", None)
    await settings_repo.set_setting("board_light_color", None)
    await settings_repo.set_setting("board_dark_color", None)
    return {"success": True}


@settings_router.get(
    "/api/settings/theme",
    response_model=ThemeColors,
    summary="Get theme colors",
    description="Retrieve the current theme color settings.",
)
async def get_theme(settings_repo: SettingsRepoDep) -> dict[str, str]:
    result = {}
    for key in THEME_KEYS:
        db_key = f"theme_{key}"
        value = await settings_repo.get_setting(db_key)
        result[key] = value or DEFAULT_THEME[key]
    return result


@settings_router.post(
    "/api/settings/theme/reset",
    response_model=SuccessResponse,
    summary="Reset theme to defaults",
    description="Reset all theme colors to their default values.",
)
async def reset_theme(settings_repo: SettingsRepoDep) -> dict[str, bool]:
    for key in THEME_KEYS:
        await settings_repo.set_setting(f"theme_{key}", None)
    return {"success": True}


@settings_router.post(
    "/api/settings",
    response_model=SuccessResponse,
    summary="Update settings",
    description="Update application settings including sync configuration and analysis preferences.",
)
async def settings_submit(
    request: Request, payload: SettingsRequest, settings_repo: SettingsRepoDep
) -> dict[str, bool]:
    await settings_repo.set_setting(
        "auto_sync_enabled", "true" if payload.auto_sync else "false"
    )
    await settings_repo.set_setting("sync_interval_hours", str(payload.sync_interval))
    await settings_repo.set_setting("sync_max_games", str(payload.max_games))
    await settings_repo.set_setting(
        "analyze_new_games_automatically", "true" if payload.auto_analyze else "false"
    )
    await settings_repo.set_setting(
        "spaced_repetition_days", str(payload.spaced_repetition_days)
    )

    if payload.theme:
        theme_dict = payload.theme.model_dump()
        for key, value in theme_dict.items():
            await settings_repo.set_setting(f"theme_{key}", value)

    scheduler = request.app.state.scheduler
    settings = await settings_repo.get_all_settings()
    scheduler.update_jobs(settings)

    return {"success": True}


class FeatureFlagsResponse(BaseModel):
    features: dict[str, bool] = Field(description="Feature visibility flags")


class FeatureFlagsRequest(BaseModel):
    features: dict[str, bool] = Field(description="Feature flags to update")


@settings_router.get(
    "/api/settings/features",
    response_model=FeatureFlagsResponse,
    summary="Get feature visibility flags",
    description="Retrieve current feature visibility settings.",
)
async def get_features(settings_repo: SettingsRepoDep) -> dict[str, Any]:
    features = await settings_repo.get_feature_flags()
    return {"features": features}


@settings_router.post(
    "/api/settings/features",
    response_model=SuccessResponse,
    summary="Update feature visibility flags",
    description="Toggle visibility of individual features.",
)
async def update_features(
    request: Request, payload: FeatureFlagsRequest, settings_repo: SettingsRepoDep
) -> dict[str, bool]:
    await settings_repo.set_feature_flags(payload.features)

    scheduler = request.app.state.scheduler
    settings = await settings_repo.get_all_settings()
    scheduler.update_jobs(settings)

    return {"success": True}


class LocaleRequest(BaseModel):
    locale: str = Field(description="Locale code (e.g., 'en', 'ru')")


@settings_router.post(
    "/api/settings/locale",
    response_model=SuccessResponse,
    summary="Set display locale",
    description="Update the application display language.",
)
async def set_locale(
    request: Request, payload: LocaleRequest, settings_repo: SettingsRepoDep
) -> JSONResponse:
    i18n = getattr(request.app.state, "i18n", None)
    if i18n and payload.locale not in i18n.available_locales():
        raise HTTPException(status_code=400, detail="Unsupported locale")
    await settings_repo.set_setting("locale", payload.locale)
    request.app.state._locale_cache = payload.locale

    response = JSONResponse(content={"success": True})
    response.set_cookie(
        key="locale",
        value=payload.locale,
        path="/",
        max_age=365 * 24 * 3600,
        samesite="lax",
    )
    return response


class DeleteAllResponse(BaseModel):
    job_id: str = Field(description="Job ID for tracking the delete operation")


@settings_router.delete(
    "/api/data/all",
    response_model=DeleteAllResponse,
    summary="Delete all data",
    description="Start a background job to delete all imported games, analysis results, puzzle attempts, and job history. Settings are preserved.",
)
async def delete_all_data(
    job_service: JobServiceDep,
    event_bus: EventBusDep,
) -> dict[str, Any]:
    job_id = await job_service.create_job(job_type="delete_all_data")

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="delete_all_data",
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
        job_type="delete_all_data", status="running", limit=1
    )

    if running_jobs:
        return running_jobs[0]

    recent_jobs = await job_service.list_jobs(job_type="delete_all_data", limit=1)

    if not recent_jobs:
        return {"status": "no_jobs"}

    return recent_jobs[0]
