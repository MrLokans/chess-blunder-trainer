from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException, Path, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

from blunder_tutor.events import JobExecutionRequestEvent
from blunder_tutor.web.api.schemas import ErrorResponse
from blunder_tutor.web.dependencies import (
    AnalysisRepoDep,
    EventBusDep,
    GameRepoDep,
    JobServiceDep,
)


class StartImportRequest(BaseModel):
    username: str = Field(description="Username to import games for")
    source: str = Field(description="Platform source ('lichess' or 'chesscom')")
    max_games: int = Field(
        default=1000, description="Maximum number of games to import"
    )


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
    payload: StartImportRequest,
    job_service: JobServiceDep,
    event_bus: EventBusDep,
) -> dict[str, str]:
    job_id = await job_service.create_job(
        job_type="import",
        username=payload.username,
        source=payload.source,
        max_games=payload.max_games,
    )

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="import",
        source=payload.source,
        username=payload.username,
        max_games=payload.max_games,
    )
    await event_bus.publish(event)

    return {"job_id": job_id}


@jobs_router.get(
    "/api/import/status/{job_id}",
    response_model=JobStatusResponse,
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
    summary="Get import status",
    description="Check the status of a specific import job.",
)
async def get_import_status(
    job_service: JobServiceDep,
    job_id: str = Path(description="Job ID to check status for"),
) -> dict[str, Any]:
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@jobs_router.post(
    "/api/sync/start",
    response_model=SyncStatusResponse,
    summary="Start sync job",
    description="Trigger a manual game synchronization.",
)
async def start_sync_job(
    job_service: JobServiceDep,
    event_bus: EventBusDep,
) -> dict[str, str]:
    job_id = await job_service.create_job(job_type="sync")

    event = JobExecutionRequestEvent.create(job_id=job_id, job_type="sync")
    await event_bus.publish(event)

    return {"status": "sync started"}


@jobs_router.get(
    "/api/sync/status",
    summary="Get sync status",
    description="Get the status of the most recent sync job.",
)
async def get_sync_status(job_service: JobServiceDep) -> dict[str, Any]:
    jobs = await job_service.list_jobs(job_type="sync", limit=1)

    if not jobs:
        return {"status": "no sync jobs"}

    return jobs[0]


@jobs_router.get(
    "/api/jobs",
    summary="List jobs",
    description="List recent jobs with optional filtering by type and status.",
)
async def list_jobs(
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
    jobs = await job_service.list_jobs(job_type=type, status=status, limit=limit)
    return jobs


@jobs_router.get(
    "/api/jobs/html",
    response_class=HTMLResponse,
    summary="Get jobs table HTML",
    description="Returns jobs table rows as HTML partial for HTMX.",
)
async def get_jobs_html(
    request: Request,
    job_service: JobServiceDep,
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of jobs to return"
    ),
) -> HTMLResponse:
    jobs = await job_service.list_jobs(limit=limit)

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
    job_service: JobServiceDep,
    game_repo: GameRepoDep,
    event_bus: EventBusDep,
) -> dict[str, str]:
    unanalyzed_game_ids = await game_repo.list_unanalyzed_game_ids()

    if not unanalyzed_game_ids:
        raise HTTPException(status_code=400, detail="No unanalyzed games found")

    job_id = await job_service.create_job(
        job_type="analyze",
        max_games=len(unanalyzed_game_ids),
    )

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="analyze",
        game_ids=unanalyzed_game_ids,
    )
    await event_bus.publish(event)

    return {"job_id": job_id}


@jobs_router.post(
    "/api/analysis/stop/{job_id}",
    summary="Stop analysis job",
    description="Stop a running analysis job.",
    responses={404: {"model": ErrorResponse, "description": "Job not found"}},
)
async def stop_analysis_job(
    job_service: JobServiceDep,
    job_id: str = Path(description="Job ID to stop"),
) -> dict[str, str]:
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] not in ("pending", "running"):
        raise HTTPException(
            status_code=400, detail=f"Cannot stop job with status: {job['status']}"
        )

    await job_service.update_job_status(job_id, "failed", "Cancelled by user")

    return {"status": "stopped", "job_id": job_id}


@jobs_router.get(
    "/api/analysis/status",
    summary="Get current analysis status",
    description="Get the status of the most recent or currently running analysis job.",
)
async def get_analysis_status(job_service: JobServiceDep) -> dict[str, Any]:
    running_jobs = await job_service.list_jobs(
        job_type="analyze", status="running", limit=1
    )

    if running_jobs:
        return running_jobs[0]

    recent_jobs = await job_service.list_jobs(job_type="analyze", limit=1)

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
async def delete_job(
    request: Request,
    job_service: JobServiceDep,
    job_id: str = Path(description="Job ID to delete"),
) -> HTMLResponse:
    job = await job_service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job["status"] == "running":
        raise HTTPException(
            status_code=400, detail="Cannot delete running jobs. Stop the job first."
        )

    deleted = await job_service.delete_job(job_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")

    jobs = await job_service.list_jobs(limit=20)

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


@jobs_router.post(
    "/api/backfill-phases/start",
    response_model=JobResponse,
    summary="Start phase backfill",
    description="Start a background job to backfill game phase data for analyzed games.",
)
async def start_backfill_phases_job(
    job_service: JobServiceDep,
    analysis_repo: AnalysisRepoDep,
    event_bus: EventBusDep,
) -> dict[str, str]:
    games_needing_backfill = await analysis_repo.get_game_ids_missing_phase()

    if not games_needing_backfill:
        raise HTTPException(status_code=400, detail="No games need phase backfill")

    job_id = await job_service.create_job(
        job_type="backfill_phases",
        max_games=len(games_needing_backfill),
    )

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="backfill_phases",
    )
    await event_bus.publish(event)

    return {"job_id": job_id}


@jobs_router.get(
    "/api/backfill-phases/status",
    summary="Get backfill phases status",
    description="Get the status of the most recent or currently running phase backfill job.",
)
async def get_backfill_phases_status(job_service: JobServiceDep) -> dict[str, Any]:
    running_jobs = await job_service.list_jobs(
        job_type="backfill_phases", status="running", limit=1
    )

    if running_jobs:
        return running_jobs[0]

    recent_jobs = await job_service.list_jobs(job_type="backfill_phases", limit=1)

    if not recent_jobs:
        return {"status": "no_jobs"}

    return recent_jobs[0]


@jobs_router.get(
    "/api/backfill-phases/pending",
    summary="Get pending backfill count",
    description="Get the number of games that need phase backfill.",
)
async def get_backfill_phases_pending(analysis_repo: AnalysisRepoDep) -> dict[str, int]:
    games_needing_backfill = await analysis_repo.get_game_ids_missing_phase()
    return {"pending_count": len(games_needing_backfill)}


@jobs_router.post(
    "/api/backfill-eco/start",
    response_model=JobResponse,
    summary="Start ECO backfill",
    description="Start a background job to backfill ECO opening codes for analyzed games.",
)
async def start_backfill_eco_job(
    job_service: JobServiceDep,
    analysis_repo: AnalysisRepoDep,
    event_bus: EventBusDep,
) -> dict[str, str]:
    games_needing_backfill = await analysis_repo.get_game_ids_missing_eco()

    if not games_needing_backfill:
        raise HTTPException(status_code=400, detail="No games need ECO backfill")

    job_id = await job_service.create_job(
        job_type="backfill_eco",
        max_games=len(games_needing_backfill),
    )

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="backfill_eco",
    )
    await event_bus.publish(event)

    return {"job_id": job_id}


@jobs_router.get(
    "/api/backfill-eco/status",
    summary="Get backfill ECO status",
    description="Get the status of the most recent or currently running ECO backfill job.",
)
async def get_backfill_eco_status(job_service: JobServiceDep) -> dict[str, Any]:
    running_jobs = await job_service.list_jobs(
        job_type="backfill_eco", status="running", limit=1
    )

    if running_jobs:
        return running_jobs[0]

    recent_jobs = await job_service.list_jobs(job_type="backfill_eco", limit=1)

    if not recent_jobs:
        return {"status": "no_jobs"}

    return recent_jobs[0]


@jobs_router.get(
    "/api/backfill-eco/pending",
    summary="Get pending ECO backfill count",
    description="Get the number of games that need ECO backfill.",
)
async def get_backfill_eco_pending(analysis_repo: AnalysisRepoDep) -> dict[str, int]:
    games_needing_backfill = await analysis_repo.get_game_ids_missing_eco()
    return {"pending_count": len(games_needing_backfill)}


@jobs_router.post(
    "/api/backfill-tactics/start",
    response_model=JobResponse,
    summary="Start tactics backfill",
    description="Start a background job to classify tactical patterns for existing blunders.",
)
async def start_backfill_tactics_job(
    job_service: JobServiceDep,
    analysis_repo: AnalysisRepoDep,
    event_bus: EventBusDep,
) -> dict[str, str]:
    games_needing_backfill = await analysis_repo.get_game_ids_missing_tactics()

    if not games_needing_backfill:
        raise HTTPException(status_code=400, detail="No games need tactics backfill")

    job_id = await job_service.create_job(
        job_type="backfill_tactics",
        max_games=len(games_needing_backfill),
    )

    event = JobExecutionRequestEvent.create(
        job_id=job_id,
        job_type="backfill_tactics",
    )
    await event_bus.publish(event)

    return {"job_id": job_id}


@jobs_router.get(
    "/api/backfill-tactics/status",
    summary="Get backfill tactics status",
    description="Get the status of the most recent or currently running tactics backfill job.",
)
async def get_backfill_tactics_status(job_service: JobServiceDep) -> dict[str, Any]:
    running_jobs = await job_service.list_jobs(
        job_type="backfill_tactics", status="running", limit=1
    )

    if running_jobs:
        return running_jobs[0]

    recent_jobs = await job_service.list_jobs(job_type="backfill_tactics", limit=1)

    if not recent_jobs:
        return {"status": "no_jobs"}

    return recent_jobs[0]


@jobs_router.get(
    "/api/backfill-tactics/pending",
    summary="Get pending tactics backfill count",
    description="Get the number of games with blunders that need tactical pattern classification.",
)
async def get_backfill_tactics_pending(
    analysis_repo: AnalysisRepoDep,
) -> dict[str, int]:
    games_needing_backfill = await analysis_repo.get_game_ids_missing_tactics()
    return {"pending_count": len(games_needing_backfill)}
