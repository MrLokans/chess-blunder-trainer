from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ProfilePreferences:
    auto_sync_enabled: bool
    sync_max_games: int | None


@dataclass(frozen=True)
class Profile:
    id: int
    platform: str
    username: str
    is_primary: bool
    created_at: str
    updated_at: str
    last_validated_at: str | None
    preferences: ProfilePreferences


@dataclass(frozen=True)
class ProfileStatSnapshot:
    mode: str
    rating: int | None
    games_count: int
    synced_at: str | None = None


class ProfileNotFoundError(LookupError):
    """Raised when a profile lookup by id finds no row."""


class ProfileRepository(Protocol):
    async def list_profiles(self) -> list[Profile]: ...
    async def get(self, profile_id: int) -> Profile | None: ...
    async def find_by_platform_username(
        self, platform: str, username: str
    ) -> Profile | None: ...
    async def create(
        self, platform: str, username: str, *, make_primary: bool = False
    ) -> Profile: ...
    async def update(
        self,
        profile_id: int,
        *,
        username: str | None = None,
        is_primary: bool | None = None,
    ) -> Profile: ...
    async def update_preferences(
        self,
        profile_id: int,
        *,
        auto_sync_enabled: bool | None = None,
        sync_max_games: int | None = None,
        clear_sync_max_games: bool = False,
    ) -> Profile: ...
    async def delete(self, profile_id: int, *, detach_games: bool) -> None: ...
    async def upsert_stats(
        self, profile_id: int, snapshots: list[ProfileStatSnapshot]
    ) -> None: ...
    async def list_stats(self, profile_id: int) -> list[ProfileStatSnapshot]: ...
    async def touch_validated_at(self, profile_id: int) -> None: ...
