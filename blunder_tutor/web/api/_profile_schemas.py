# flake8: noqa: WPS202
# Pydantic request/response schemas for every /api/profiles/* endpoint.
# All members are part of one resource's API contract; splitting across
# files would just spread cross-references with no clarity gain.
from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator

USERNAME_MAX_LEN = 64


class ProfileValidateRequest(BaseModel):
    platform: Literal["lichess", "chesscom"]
    username: str = Field(..., min_length=1, max_length=USERNAME_MAX_LEN)


class ProfileValidateResponse(BaseModel):
    exists: bool
    already_tracked: bool
    profile_id: int | None
    rate_limited: bool


class StatsSnapshotShape(BaseModel):
    mode: str
    rating: int | None
    games_count: int
    # Nullable because the DB column is nullable. Frontends MUST treat
    # `null` as "no sync recorded" — never an empty string.
    synced_at: str | None


class PreferencesShape(BaseModel):
    auto_sync_enabled: bool
    sync_max_games: int | None


class ProfileShape(BaseModel):
    id: int
    platform: str
    username: str
    is_primary: bool
    created_at: str
    last_validated_at: str | None
    preferences: PreferencesShape
    stats: list[StatsSnapshotShape]
    last_game_sync_at: str | None
    last_stats_sync_at: str | None


class ProfilesListResponse(BaseModel):
    profiles: list[ProfileShape]


class ProfileSyncDispatchResponse(BaseModel):
    job_id: str = Field(
        description="ID of the background_jobs row created for this sync. "
        "UI polls /api/import/status/{job_id} for progress."
    )


class ProfileStatsRefreshResponse(BaseModel):
    stats: list[StatsSnapshotShape]
    last_validated_at: str | None


class ProfileCreateRequest(BaseModel):
    platform: Literal["lichess", "chesscom"]
    username: str = Field(..., min_length=1, max_length=USERNAME_MAX_LEN)
    make_primary: bool = False


class PreferencesPatch(BaseModel):
    # Default-None means "field absent". Distinguish via `model_fields_set`.
    # `auto_sync_enabled` rejects explicit null (validator below).
    # `sync_max_games` accepts explicit null as "clear (use global default)".
    auto_sync_enabled: bool | None = None
    sync_max_games: int | None = None

    @model_validator(mode="after")
    def _reject_null_auto_sync(self) -> Self:
        if (
            "auto_sync_enabled" in self.model_fields_set
            and self.auto_sync_enabled is None
        ):
            raise ValueError(
                "auto_sync_enabled cannot be null (omit the field to leave unchanged)"
            )
        return self


class RatingPointShape(BaseModel):
    end_time_utc: str
    rating: int
    game_type: str
    color: Literal["white", "black"]
    opponent_rating: int | None


class RatingHistoryResponse(BaseModel):
    points: list[RatingPointShape]


class ProfileUpdateRequest(BaseModel):
    username: str | None = Field(
        default=None, min_length=1, max_length=USERNAME_MAX_LEN
    )
    is_primary: bool | None = None
    preferences: PreferencesPatch | None = None

    @model_validator(mode="after")
    def _reject_explicit_null_identity_fields(self) -> Self:
        fields = self.model_fields_set
        if "username" in fields and self.username is None:
            raise ValueError(
                "username cannot be null (omit the field to leave unchanged)"
            )
        if "is_primary" in fields and self.is_primary is None:
            raise ValueError(
                "is_primary cannot be null (omit the field to leave unchanged)"
            )
        return self
