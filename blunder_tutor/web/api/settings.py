from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from blunder_tutor.events import JobExecutionRequestEvent
from blunder_tutor.web.api.schemas import ErrorResponse, SuccessResponse
from blunder_tutor.web.dependencies import EventBusDep, JobServiceDep, SettingsRepoDep


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
    lichess: str = Field(default="", description="Lichess username")
    chesscom: str = Field(default="", description="Chess.com username")
    auto_sync: bool = Field(default=False, description="Enable automatic game sync")
    sync_interval: int = Field(
        default=24, ge=1, le=168, description="Sync interval in hours"
    )
    max_games: int = Field(
        default=1000, ge=1, le=10000, description="Maximum games to sync"
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
    max_games: int = Field(default=1000, description="Max games to sync")
    auto_analyze: bool = Field(default=True, description="Auto analyze new games")
    spaced_repetition_days: int = Field(
        default=30, description="Spaced repetition days"
    )


settings_router = APIRouter()


@settings_router.post(
    "/api/setup",
    response_model=SuccessResponse,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least one username is required",
        }
    },
    summary="Complete initial setup",
    description="Configure usernames for Lichess and/or Chess.com accounts.",
)
async def setup_submit(
    request: Request, payload: SetupRequest, settings_repo: SettingsRepoDep
) -> dict[str, bool]:
    lichess = payload.lichess.strip()
    chesscom = payload.chesscom.strip()

    if not lichess and not chesscom:
        raise HTTPException(
            status_code=400,
            detail="At least one username is required (Lichess or Chess.com)",
        )

    await settings_repo.set_setting("lichess_username", lichess if lichess else None)
    await settings_repo.set_setting("chesscom_username", chesscom if chesscom else None)
    await settings_repo.mark_setup_completed()

    if hasattr(request.app.state, "_setup_completed_cache"):
        delattr(request.app.state, "_setup_completed_cache")

    return {"success": True}


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
        "max_games": int(settings.get("sync_max_games", "1000")),
        "auto_analyze": settings.get("analyze_new_games_automatically", "true")
        == "true",
        "spaced_repetition_days": int(settings.get("spaced_repetition_days", "30")),
    }


DEFAULT_THEME = {
    "primary": "#4f6d7a",
    "success": "#3d8b6e",
    "error": "#c25450",
    "warning": "#b8860b",
    "phase_opening": "#5b8a9a",
    "phase_middlegame": "#9a7b5b",
    "phase_endgame": "#7a5b9a",
    "bg": "#f1f5f9",
    "bg_card": "#ffffff",
    "text": "#1e293b",
    "text_muted": "#64748b",
    "heatmap_empty": "#ebedf0",
    "heatmap_l1": "#9be9a8",
    "heatmap_l2": "#40c463",
    "heatmap_l3": "#30a14e",
    "heatmap_l4": "#216e39",
}

THEME_PRESETS = {
    "default": {
        "name": "Default",
        "description": "Muted slate tones for a calm, professional look",
        "colors": DEFAULT_THEME,
    },
    "ocean": {
        "name": "Ocean",
        "description": "Cool blue tones inspired by the sea",
        "colors": {
            "primary": "#0077b6",
            "success": "#2a9d8f",
            "error": "#e63946",
            "warning": "#e9c46a",
            "phase_opening": "#48cae4",
            "phase_middlegame": "#0096c7",
            "phase_endgame": "#023e8a",
            "bg": "#f0f9ff",
            "bg_card": "#ffffff",
            "text": "#03045e",
            "text_muted": "#4a6fa5",
            "heatmap_empty": "#e0f2fe",
            "heatmap_l1": "#7dd3fc",
            "heatmap_l2": "#38bdf8",
            "heatmap_l3": "#0284c7",
            "heatmap_l4": "#0369a1",
        },
    },
    "forest": {
        "name": "Forest",
        "description": "Natural greens and earth tones",
        "colors": {
            "primary": "#2d6a4f",
            "success": "#40916c",
            "error": "#9b2226",
            "warning": "#bc6c25",
            "phase_opening": "#52b788",
            "phase_middlegame": "#8b5e3c",
            "phase_endgame": "#6c584c",
            "bg": "#f5f5f0",
            "bg_card": "#fefefe",
            "text": "#1b4332",
            "text_muted": "#5c7a5c",
            "heatmap_empty": "#d8f3dc",
            "heatmap_l1": "#95d5b2",
            "heatmap_l2": "#52b788",
            "heatmap_l3": "#2d6a4f",
            "heatmap_l4": "#1b4332",
        },
    },
    "sunset": {
        "name": "Sunset",
        "description": "Warm oranges and reds",
        "colors": {
            "primary": "#d35400",
            "success": "#27ae60",
            "error": "#c0392b",
            "warning": "#f39c12",
            "phase_opening": "#e67e22",
            "phase_middlegame": "#d35400",
            "phase_endgame": "#a04000",
            "bg": "#fdf6e9",
            "bg_card": "#ffffff",
            "text": "#2c1810",
            "text_muted": "#7f6855",
            "heatmap_empty": "#fef3c7",
            "heatmap_l1": "#fcd34d",
            "heatmap_l2": "#f59e0b",
            "heatmap_l3": "#d97706",
            "heatmap_l4": "#b45309",
        },
    },
    "lavender": {
        "name": "Lavender",
        "description": "Soft purples and gentle tones",
        "colors": {
            "primary": "#7c3aed",
            "success": "#059669",
            "error": "#dc2626",
            "warning": "#d97706",
            "phase_opening": "#8b5cf6",
            "phase_middlegame": "#a78bfa",
            "phase_endgame": "#6d28d9",
            "bg": "#f5f3ff",
            "bg_card": "#ffffff",
            "text": "#1e1b4b",
            "text_muted": "#6b7280",
            "heatmap_empty": "#ede9fe",
            "heatmap_l1": "#c4b5fd",
            "heatmap_l2": "#a78bfa",
            "heatmap_l3": "#7c3aed",
            "heatmap_l4": "#5b21b6",
        },
    },
    "monochrome": {
        "name": "Monochrome",
        "description": "Clean grayscale aesthetic",
        "colors": {
            "primary": "#374151",
            "success": "#4b5563",
            "error": "#6b7280",
            "warning": "#9ca3af",
            "phase_opening": "#6b7280",
            "phase_middlegame": "#4b5563",
            "phase_endgame": "#374151",
            "bg": "#f3f4f6",
            "bg_card": "#ffffff",
            "text": "#111827",
            "text_muted": "#6b7280",
            "heatmap_empty": "#e5e7eb",
            "heatmap_l1": "#9ca3af",
            "heatmap_l2": "#6b7280",
            "heatmap_l3": "#4b5563",
            "heatmap_l4": "#1f2937",
        },
    },
    "dark": {
        "name": "Dark",
        "description": "Easy on the eyes in low light",
        "colors": {
            "primary": "#60a5fa",
            "success": "#34d399",
            "error": "#f87171",
            "warning": "#fbbf24",
            "phase_opening": "#38bdf8",
            "phase_middlegame": "#fb923c",
            "phase_endgame": "#a78bfa",
            "bg": "#0f172a",
            "bg_card": "#1e293b",
            "text": "#f1f5f9",
            "text_muted": "#94a3b8",
            "heatmap_empty": "#1e293b",
            "heatmap_l1": "#064e3b",
            "heatmap_l2": "#047857",
            "heatmap_l3": "#10b981",
            "heatmap_l4": "#34d399",
        },
    },
    "high_contrast": {
        "name": "High Contrast",
        "description": "Maximum readability and accessibility",
        "colors": {
            "primary": "#0000ee",
            "success": "#008000",
            "error": "#cc0000",
            "warning": "#cc8800",
            "phase_opening": "#0066cc",
            "phase_middlegame": "#cc6600",
            "phase_endgame": "#6600cc",
            "bg": "#ffffff",
            "bg_card": "#ffffff",
            "heatmap_empty": "#d4d4d4",
            "heatmap_l1": "#a3e635",
            "heatmap_l2": "#65a30d",
            "heatmap_l3": "#3f6212",
            "heatmap_l4": "#1a2e05",
            "text": "#000000",
            "text_muted": "#333333",
        },
    },
}

THEME_KEYS = list(DEFAULT_THEME.keys())


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
    responses={
        400: {
            "model": ErrorResponse,
            "description": "At least one username is required",
        }
    },
    summary="Update settings",
    description="Update application settings including usernames, sync configuration, and analysis preferences.",
)
async def settings_submit(
    request: Request, payload: SettingsRequest, settings_repo: SettingsRepoDep
) -> dict[str, bool]:
    lichess = payload.lichess.strip()
    chesscom = payload.chesscom.strip()

    if not lichess and not chesscom:
        raise HTTPException(
            status_code=400,
            detail="At least one username is required (Lichess or Chess.com)",
        )

    await settings_repo.set_setting("lichess_username", lichess if lichess else None)
    await settings_repo.set_setting("chesscom_username", chesscom if chesscom else None)

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
