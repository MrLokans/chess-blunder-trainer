from __future__ import annotations

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    error: str = Field(description="Error message")
    detail: str = Field(default="", description="Additional error details")


class SuccessResponse(BaseModel):
    success: bool = Field(description="Operation success status")
