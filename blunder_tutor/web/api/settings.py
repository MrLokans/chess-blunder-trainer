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


class UsernamesResponse(BaseModel):
    lichess_username: str | None = Field(
        None, description="Configured Lichess username"
    )
    chesscom_username: str | None = Field(
        None, description="Configured Chess.com username"
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
async def get_settings(settings_repo: SettingsRepoDep) -> dict[str, Any]:
    usernames = await settings_repo.get_configured_usernames()

    return {
        "lichess_username": usernames.get("lichess"),
        "chesscom_username": usernames.get("chesscom"),
    }


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
