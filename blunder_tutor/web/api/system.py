from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

system_router = APIRouter()


class EngineStatusResponse(BaseModel):
    available: bool = Field(description="Whether the engine is accessible")
    name: str | None = Field(None, description="Engine name")
    author: str | None = Field(None, description="Engine author")
    path: str | None = Field(None, description="Configured engine path")


@system_router.get(
    "/api/system/engine",
    response_model=EngineStatusResponse,
    summary="Get chess engine status",
    description="Returns information about the configured chess engine (Stockfish).",
)
async def get_engine_status(request: Request) -> dict[str, Any]:
    engine = getattr(request.app.state, "engine", None)
    config = getattr(request.app.state, "config", None)
    engine_path = config.engine_path if config else None

    if engine is None:
        return {
            "available": False,
            "name": None,
            "author": None,
            "path": engine_path,
        }

    engine_id = getattr(engine, "id", {})
    return {
        "available": True,
        "name": engine_id.get("name"),
        "author": engine_id.get("author"),
        "path": engine_path,
    }
