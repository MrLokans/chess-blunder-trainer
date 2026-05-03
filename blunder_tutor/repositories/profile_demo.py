"""In-memory `ProfileRepository` for demo mode.

Process-wide singleton — mutations are visible to every concurrent demo
viewer until the next process restart. Documented as a v1 trade-off in
the design spec; revisit if abuse appears.
"""

# flake8: noqa: WPS202

from __future__ import annotations

import asyncio

from blunder_tutor.repositories.profile_types import (
    Profile,
    ProfileNotFoundError,
    ProfilePreferences,
    ProfileStatSnapshot,
    ProfileSyncCandidate,
)
from blunder_tutor.utils.time import now_iso

_DEMO_SEED_LICHESS_STATS: tuple[ProfileStatSnapshot, ...] = (
    ProfileStatSnapshot(mode="bullet", rating=2400, games_count=3120, synced_at=None),  # noqa: WPS432 — fixture data, not a magic number.
    ProfileStatSnapshot(mode="blitz", rating=2350, games_count=8204, synced_at=None),  # noqa: WPS432
    ProfileStatSnapshot(mode="rapid", rating=2280, games_count=1452, synced_at=None),  # noqa: WPS432
)

_DEMO_SEED_CHESSCOM_STATS: tuple[ProfileStatSnapshot, ...] = (
    ProfileStatSnapshot(mode="blitz", rating=2200, games_count=4080, synced_at=None),  # noqa: WPS432
    ProfileStatSnapshot(mode="rapid", rating=2150, games_count=2210, synced_at=None),  # noqa: WPS432
    ProfileStatSnapshot(
        mode="correspondence",
        rating=1900,
        games_count=88,
        synced_at=None,  # noqa: WPS432
    ),
)


def _require_profile(store: dict[int, Profile], profile_id: int) -> Profile:
    """Single raise-site for `ProfileNotFoundError` so the constructor is
    only invoked from one place. Kept module-level so multiple repo
    methods can share it.
    """
    profile = store.get(profile_id)
    if profile is None:
        raise ProfileNotFoundError(profile_id)
    return profile


class InMemoryProfileRepository:
    """Demo-mode `ProfileRepository`. Process-wide singleton; not per-session.

    Seeds two example profiles on construction so a first-page load shows
    something meaningful instead of the empty state.
    """

    def __init__(self) -> None:
        self._profiles: dict[int, Profile] = {}
        self._stats: dict[int, list[ProfileStatSnapshot]] = {}
        self._next_id: int = 1
        self._lock = asyncio.Lock()
        self._seed()

    async def list_profiles(self) -> list[Profile]:
        return sorted(
            self._profiles.values(),
            key=lambda p: (p.platform, not p.is_primary, p.username),
        )

    async def get(self, profile_id: int) -> Profile | None:
        return self._profiles.get(profile_id)

    async def find_by_platform_username(
        self, platform: str, username: str
    ) -> Profile | None:
        normalized = username.lower()
        for profile in self._profiles.values():
            if profile.platform == platform and profile.username == normalized:
                return profile
        return None

    async def create(
        self, platform: str, username: str, *, make_primary: bool = False
    ) -> Profile:
        normalized = username.lower()
        async with self._lock:
            for existing in self._profiles.values():
                if existing.platform == platform and existing.username == normalized:
                    raise ValueError(f"profile already exists: {platform}/{normalized}")
            now = now_iso()
            has_primary = any(
                p.platform == platform and p.is_primary for p in self._profiles.values()
            )
            should_be_primary = make_primary or not has_primary
            if should_be_primary and has_primary:
                self._demote_primaries(platform)
            new_profile = Profile(
                id=self._allocate_id(),
                platform=platform,
                username=normalized,
                is_primary=should_be_primary,
                created_at=now,
                updated_at=now,
                last_validated_at=None,
                preferences=ProfilePreferences(
                    auto_sync_enabled=True, sync_max_games=None
                ),
            )
            self._profiles[new_profile.id] = new_profile
            self._stats[new_profile.id] = []
            return new_profile

    async def update(
        self,
        profile_id: int,
        *,
        username: str | None = None,
        is_primary: bool | None = None,
    ) -> Profile:
        async with self._lock:
            current = _require_profile(self._profiles, profile_id)
            new_username = (
                username.lower() if username is not None else current.username
            )
            new_is_primary = (
                is_primary if is_primary is not None else current.is_primary
            )
            if is_primary is True:
                self._demote_primaries(current.platform, except_id=profile_id)
            updated = Profile(
                id=current.id,
                platform=current.platform,
                username=new_username,
                is_primary=new_is_primary,
                created_at=current.created_at,
                updated_at=now_iso(),
                last_validated_at=current.last_validated_at,
                preferences=current.preferences,
            )
            self._profiles[profile_id] = updated
            return updated

    async def update_preferences(
        self,
        profile_id: int,
        *,
        auto_sync_enabled: bool | None = None,
        sync_max_games: int | None = None,
        clear_sync_max_games: bool = False,
    ) -> Profile:
        if clear_sync_max_games and sync_max_games is not None:
            raise ValueError(
                "clear_sync_max_games and sync_max_games are mutually exclusive"
            )
        async with self._lock:
            current = _require_profile(self._profiles, profile_id)
            new_auto = (
                auto_sync_enabled
                if auto_sync_enabled is not None
                else current.preferences.auto_sync_enabled
            )
            if clear_sync_max_games:
                new_max: int | None = None
            elif sync_max_games is not None:
                new_max = sync_max_games
            else:
                new_max = current.preferences.sync_max_games
            updated = Profile(
                id=current.id,
                platform=current.platform,
                username=current.username,
                is_primary=current.is_primary,
                created_at=current.created_at,
                updated_at=now_iso(),
                last_validated_at=current.last_validated_at,
                preferences=ProfilePreferences(
                    auto_sync_enabled=new_auto, sync_max_games=new_max
                ),
            )
            self._profiles[profile_id] = updated
            return updated

    async def delete(self, profile_id: int, *, detach_games: bool) -> None:
        # `detach_games` is part of the protocol but irrelevant in demo —
        # there are no game rows to detach or cascade-delete in this
        # in-memory store.
        del detach_games
        async with self._lock:
            _require_profile(self._profiles, profile_id)
            self._profiles.pop(profile_id, None)
            self._stats.pop(profile_id, None)

    async def upsert_stats(
        self, profile_id: int, snapshots: list[ProfileStatSnapshot]
    ) -> None:
        # Per the design spec: keep seeded values stable across job runs
        # in demo mode. The runner-side stats refresh will still report
        # success; the demo-visible numbers stay.
        del snapshots
        _require_profile(self._profiles, profile_id)

    async def list_stats(self, profile_id: int) -> list[ProfileStatSnapshot]:
        return list(self._stats.get(profile_id, ()))

    async def list_auto_sync_candidates(self) -> list[ProfileSyncCandidate]:
        # Demo mode does not auto-sync; the scheduler still calls this
        # on its tick, so return an empty list rather than raising.
        return []

    async def touch_validated_at(self, profile_id: int) -> None:
        async with self._lock:
            current = _require_profile(self._profiles, profile_id)
            self._profiles[profile_id] = Profile(
                id=current.id,
                platform=current.platform,
                username=current.username,
                is_primary=current.is_primary,
                created_at=current.created_at,
                updated_at=now_iso(),
                last_validated_at=now_iso(),
                preferences=current.preferences,
            )

    def _allocate_id(self) -> int:
        out = self._next_id
        self._next_id += 1
        return out

    def _demote_primaries(self, platform: str, *, except_id: int | None = None) -> None:
        for pid, profile in list(self._profiles.items()):
            if profile.platform != platform or pid == except_id:
                continue
            if not profile.is_primary:
                continue
            self._profiles[pid] = Profile(
                id=profile.id,
                platform=profile.platform,
                username=profile.username,
                is_primary=False,
                created_at=profile.created_at,
                updated_at=now_iso(),
                last_validated_at=profile.last_validated_at,
                preferences=profile.preferences,
            )

    def _seed(self) -> None:
        now = now_iso()
        lichess = Profile(
            id=self._allocate_id(),
            platform="lichess",
            username="demouser_li",
            is_primary=True,
            created_at=now,
            updated_at=now,
            last_validated_at=now,
            preferences=ProfilePreferences(
                auto_sync_enabled=False, sync_max_games=None
            ),
        )
        chesscom = Profile(
            id=self._allocate_id(),
            platform="chesscom",
            username="demouser_cc",
            is_primary=True,
            created_at=now,
            updated_at=now,
            last_validated_at=now,
            preferences=ProfilePreferences(
                auto_sync_enabled=False, sync_max_games=None
            ),
        )
        self._profiles[lichess.id] = lichess
        self._profiles[chesscom.id] = chesscom
        self._stats[lichess.id] = list(_DEMO_SEED_LICHESS_STATS)
        self._stats[chesscom.id] = list(_DEMO_SEED_CHESSCOM_STATS)


# Mutable container for the process-wide demo repo. Wrapping the slot in a
# list dodges the `global` statement (and ruff's PLW0603) while preserving
# the single-instance contract — every caller goes through the helpers.
_demo_repo_slot: list[InMemoryProfileRepository | None] = [None]


def get_demo_profile_repository() -> InMemoryProfileRepository:
    """Lazily construct the process-wide demo repo on first request."""
    if _demo_repo_slot[0] is None:
        _demo_repo_slot[0] = InMemoryProfileRepository()
    return _demo_repo_slot[0]


def reset_demo_profile_repository() -> None:
    """Reset the singleton — only for tests that need a fresh seed."""
    _demo_repo_slot[0] = None
