from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from fastapi import HTTPException, Path, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from blunder_tutor.web.api.schemas import ErrorResponse
from blunder_tutor.web.dependencies import (
    AnalyzeGamesJobDep,
    GameRepoDep,
    ImportGamesJobDep,
    JobServiceDep,
    SyncGamesJobDep,
)


class StartImportRequest(BaseModel):
    username: str = Field(description="Username to import games for")
    source: str = Field(description="Platform source ('lichess' or 'chesscom')")
    max_games: int = Field(
        default=1000, description="Maximum number of games to import"
    )


# Response schemas
class JobResponse(BaseModel):
    job_id: str = Field(description="Unique job identifier")


class JobStatusResponse(BaseModel):
    job_id: str = Field(description="Unique job identifier")
    job_type: str = Field(description="Type of job (import, sync, analysis)")
    status: str = Field(description="Job status (pending, running, completed, failed)")
    username: str | None = Field(None, description="Username associated with the job")
    source: str | None = Field(None, description="Platform source")
    progress: int | None = Field(None, description="Progress percentage")
    message: str | None = Field(None, description="Status message")


class SyncStatusResponse(BaseModel):
    status: str = Field(description="Sync status message")


jobs_router = APIRouter()


@jobs_router.post(
    "/api/import/start",
    response_model=JobResponse,
    summary="Start game import",
    description="Start a background job to import games from a chess platform.",
)
async def start_import_job(
    request: Request,
    payload: StartImportRequest,
    job_service: JobServiceDep,
    import_job: ImportGamesJobDep,
) -> dict[str, str]:
    # Create job and get the job_id
    job_id = job_service.create_job(
        job_type="import",
        username=payload.username,
        source=payload.source,
        max_games=payload.max_games,
    )

    # Start job in background
    asyncio.create_task(
        import_job.execute(
            job_id=job_id,
            source=payload.source,
            username=payload.username,
            max_games=payload.max_games,
        )
    )

    return {"job_id": job_id}


@jobs_router.get(
    "/api/import/status/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
    summary="Get import status",
    description="Check the status of a specific import job.",
)
def get_import_status(
    job_service: JobServiceDep,
    job_id: str = Path(description="Job ID to check status for"),
) -> dict[str, Any]:
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@jobs_router.post(
    "/api/sync/start",
    response_model=SyncStatusResponse,
    summary="Start sync job",
    description="Trigger a manual game synchronization.",
)
async def start_sync_job(sync_job: SyncGamesJobDep) -> dict[str, str]:
    """POST /api/sync/start - Trigger manual sync."""
    # Run sync in background (job_id is created per-source inside execute)
    asyncio.create_task(sync_job.execute(job_id=""))

    return {"status": "sync started"}


@jobs_router.get(
    "/api/sync/status",
    summary="Get sync status",
    description="Get the status of the most recent sync job.",
)
def get_sync_status(job_service: JobServiceDep) -> dict[str, Any]:
    # Get most recent sync job
    jobs = job_service.list_jobs(job_type="sync", limit=1)

    if not jobs:
        return {"status": "no sync jobs"}

    return jobs[0]


@jobs_router.get(
    "/api/jobs",
    summary="List jobs",
    description="List recent jobs with optional filtering by type and status.",
)
def list_jobs(
    job_service: JobServiceDep,
    type: str | None = Query(
        None, description="Filter by job type (import, sync, analysis)", alias="type"
    ),
    status: str | None = Query(
        None, description="Filter by status (pending, running, completed, failed)"
    ),
    limit: int = Query(
        50, ge=1, le=500, description="Maximum number of jobs to return"
    ),
) -> list[dict[str, Any]]:
    jobs = job_service.list_jobs(job_type=type, status=status, limit=limit)
    return jobs


@jobs_router.get(
    "/api/jobs/html",
    response_class=HTMLResponse,
    summary="Get jobs table HTML",
    description="Returns jobs table rows as HTML partial for HTMX.",
)
def get_jobs_html(
    request: Request,
    job_service: JobServiceDep,
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of jobs to return"
    ),
) -> HTMLResponse:
    jobs = job_service.list_jobs(limit=limit)

    # Format dates for display
    for job in jobs:
        if job.get("created_at"):
            try:
                dt = datetime.fromisoformat(job["created_at"])
                job["created_at_formatted"] = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                job["created_at_formatted"] = job["created_at"]
        else:
            job["created_at_formatted"] = "-"

    return request.app.state.templates.TemplateResponse(
        "_jobs_partial.html",
        {"request": request, "jobs": jobs},
    )


@jobs_router.post(
    "/api/analysis/start",
    response_model=JobResponse,
    summary="Start bulk analysis",
    description="Start a background job to analyze all unanalyzed games.",
)
async def start_analysis_job(
    request: Request,
    job_service: JobServiceDep,
    game_repo: GameRepoDep,
    analyze_job: AnalyzeGamesJobDep,
) -> dict[str, str]:
    """POST /api/analysis/start - Start bulk game analysis."""
    unanalyzed_game_ids = game_repo.list_unanalyzed_game_ids()

    if not unanalyzed_game_ids:
        raise HTTPException(status_code=400, detail="No unanalyzed games found")

    job_id = job_service.create_job(
        job_type="analyze",
        max_games=len(unanalyzed_game_ids),
    )

    asyncio.create_task(
        analyze_job.execute(job_id=job_id, game_ids=unanalyzed_game_ids)
    )

    return {"job_id": job_id}


@jobs_router.post(
    "/api/analysis/stop/{job_id}",
    summary="Stop analysis job",
    description="Stop a running analysis job.",
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
)
def stop_analysis_job(
    job_service: JobServiceDep,
    job_id: str = Path(description="Job ID to stop"),
) -> dict[str, str]:
    """POST /api/analysis/stop/{job_id} - Stop an analysis job."""
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] not in ("pending", "running"):
        raise HTTPException(
            status_code=400, detail=f"Cannot stop job with status: {job['status']}"
        )

    # Mark job as failed with cancellation message
    job_service.update_job_status(job_id, "failed", "Cancelled by user")

    return {"status": "stopped", "job_id": job_id}


@jobs_router.get(
    "/api/analysis/status",
    summary="Get current analysis status",
    description="Get the status of the most recent or currently running analysis job.",
)
def get_analysis_status(job_service: JobServiceDep) -> dict[str, Any]:
    running_jobs = job_service.list_jobs(job_type="analyze", status="running", limit=1)

    if running_jobs:
        return running_jobs[0]

    # Otherwise, get the most recent analyze job
    recent_jobs = job_service.list_jobs(job_type="analyze", limit=1)

    if not recent_jobs:
        return {"status": "no_jobs"}

    return recent_jobs[0]


@jobs_router.delete(
    "/api/jobs/{job_id}",
    summary="Delete a job",
    description="Delete a job from the database. Only running jobs cannot be deleted.",
    responses={
        404: {"model": ErrorResponse, "description": "Job not found"},
        400: {"model": ErrorResponse, "description": "Cannot delete running job"},
    },
)
def delete_job(
    request: Request,
    job_service: JobServiceDep,
    job_id: str = Path(description="Job ID to delete"),
) -> HTMLResponse:
    job = job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Prevent deletion of running jobs only
    if job["status"] == "running":
        raise HTTPException(
            status_code=400, detail="Cannot delete running jobs. Stop the job first."
        )

    # Delete the job
    deleted = job_service.delete_job(job_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

    # Return updated jobs table for HTMX
    jobs = job_service.list_jobs(limit=20)

    for j in jobs:
        if j.get("created_at"):
            try:
                dt = datetime.fromisoformat(j["created_at"])
                j["created_at_formatted"] = dt.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                j["created_at_formatted"] = j["created_at"]
        else:
            j["created_at_formatted"] = "-"

    return request.app.state.templates.TemplateResponse(
        "_jobs_partial.html",
        {"request": request, "jobs": jobs},
    )
