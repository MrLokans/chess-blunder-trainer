from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.auth import UserId
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.constants import PLATFORM_CHESSCOM, PLATFORM_LICHESS
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobExecutionRequestEvent
from blunder_tutor.fetchers import chesscom, lichess
from blunder_tutor.repositories.profile_types import Profile

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.profile import SqliteProfileRepository
    from blunder_tutor.repositories.settings import SettingsRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)

_DEFAULT_MAX_GAMES = 1000
_VALID_SOURCES: frozenset[str] = frozenset((PLATFORM_LICHESS, PLATFORM_CHESSCOM))

# Fetcher return shape: (games, metadata). Hoisted out of the function
# signature so the annotation depth doesn't trip WPS234.
GameRow = dict[str, object]
FetchResult = tuple[list[GameRow], Any]


def _import_result(stored: int, skipped: int) -> dict[str, int]:
    return {"stored": stored, "skipped": skipped}  # noqa: WPS226 — dict keys are the job-result API contract.


async def _fetch_games(
    source: str,
    username: str,
    max_games: int,
    progress_callback: Any,
) -> FetchResult:
    """Dynamic dispatch over ``lichess.fetch`` / ``chesscom.fetch``.

    Looked up at call time (not via a captured-reference dict) so tests can
    `monkeypatch.setattr` the underlying fetcher modules.
    """
    if source == PLATFORM_LICHESS:
        return await lichess.fetch(
            username, max_games, progress_callback=progress_callback
        )
    if source == PLATFORM_CHESSCOM:
        return await chesscom.fetch(
            username, max_games, progress_callback=progress_callback
        )
    raise ValueError(f"Unknown source: {source}")


@register_job
class ImportGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "import"

    def __init__(  # noqa: WPS211 — DI surface; each repo is a separate dependency.
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        profile_repo: SqliteProfileRepository,
        user_id: UserId,
        event_bus: EventBus | None = None,
    ) -> None:
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.profile_repo = profile_repo
        self.user_id = user_id
        self.event_bus = event_bus

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        profile_id = kwargs.get("profile_id")
        if profile_id is not None:
            return await self._execute_for_profile(job_id, int(profile_id))
        # /api/setup has been removed; the remaining caller of the legacy
        # source/username payload is /api/import/start (Bulk Import). Drop
        # this branch + helpers when TREK-113 replaces ImportSection with
        # BulkImportPanel (which dispatches via /api/profiles/{id}/sync).
        # `info` rather than `warning` because the legacy path is the
        # *expected* state for the entire transition window.
        logger.info(
            f"import {job_id}: legacy payload without profile_id — "
            f"rows inserted with profile_id=NULL"
        )
        return await self._execute_legacy(job_id, kwargs)

    async def _execute_for_profile(
        self, job_id: str, profile_id: int
    ) -> dict[str, Any]:
        profile = await self.profile_repo.get(profile_id)
        if profile is None:
            logger.warning(f"import {job_id}: profile {profile_id} not found, skipping")
            return _import_result(stored=0, skipped=0)

        max_games = await self._resolve_max_games_for_profile(profile)
        result = await self.job_service.run_with_lifecycle(
            job_id,
            max_games,
            lambda progress: self._import(
                profile.platform,
                profile.username,
                max_games,
                progress,
                profile_id=profile.id,
            ),
        )
        await self._trigger_auto_analysis(
            profile.platform, profile.username, int(result["stored"])
        )
        return result

    # _execute_legacy and its helpers (_resolve_max_games override path,
    # _required_source_and_username) are the legacy username-pair
    # entry-point — now only reached via /api/import/start (Bulk Import).
    # Delete this method, the `override` branch in _resolve_max_games, and
    # _required_source_and_username when TREK-113's BulkImportPanel
    # replaces ImportSection (dispatching via /api/profiles/{id}/sync
    # instead). Rows inserted by this branch get profile_id=NULL; the
    # cleanup migration backfills them by (source, username) match.
    async def _execute_legacy(
        self, job_id: str, kwargs: dict[str, Any]
    ) -> dict[str, Any]:
        source, username = _required_source_and_username(kwargs)
        max_games = await self._resolve_max_games(kwargs.get("max_games"))

        result = await self.job_service.run_with_lifecycle(
            job_id,
            max_games,
            lambda progress: self._import(source, username, max_games, progress),
        )
        await self._trigger_auto_analysis(source, username, int(result["stored"]))
        return result

    async def _resolve_max_games(self, override: object) -> int:
        if override is not None:
            return int(override)  # type: ignore[arg-type]
        max_games_str = await self.settings_repo.read_setting("sync_max_games")
        return int(max_games_str) if max_games_str else _DEFAULT_MAX_GAMES

    async def _resolve_max_games_for_profile(self, profile: Profile) -> int:
        per_profile = profile.preferences.sync_max_games
        if per_profile is not None:
            return per_profile
        return await self._resolve_max_games(None)

    async def _import(  # noqa: WPS211 — explicit parameters keep the call-site readable.
        self,
        source: str,
        username: str,
        max_games: int,
        progress: ProgressCallback,
        *,
        profile_id: int | None = None,
    ) -> dict[str, Any]:
        async def fetcher_progress(current: int, _total: int) -> None:  # noqa: WPS430 — fetcher API expects (current, total); we forward current to our progress(int) shape.
            await progress(current)

        games, _ = await _fetch_games(source, username, max_games, fetcher_progress)

        inserted = await self.game_repo.insert_games(games, profile_id=profile_id)
        await progress(len(games))
        return _import_result(stored=inserted, skipped=len(games) - inserted)

    async def _trigger_auto_analysis(
        self,
        source: str,
        username: str,
        inserted: int,
    ) -> None:
        if inserted <= 0 or self.event_bus is None:
            return

        auto_analyze = await self.settings_repo.read_setting(
            "analyze_new_games_automatically"
        )
        if auto_analyze != "true":
            return

        logger.info(f"Auto-triggering analysis for {inserted} new games")

        analyze_job_id = await self.job_service.create_job(
            job_type="analyze",
            username=username,
            source=source,
            max_games=inserted,
        )
        event = JobExecutionRequestEvent.create(
            job_id=analyze_job_id,
            job_type="analyze",
            user_id=self.user_id,
            source=source,
            username=username,
        )
        await self.event_bus.publish(event)


def _required_source_and_username(kwargs: dict[str, Any]) -> tuple[str, str]:
    source = kwargs.get("source")
    if not source:
        raise ValueError("source is required")
    username = kwargs.get("username")
    if not username:
        raise ValueError("username is required")
    if source not in _VALID_SOURCES:
        raise ValueError(f"Unknown source: {source}")
    return source, username
