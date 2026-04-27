from __future__ import annotations

import logging
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, ClassVar

from blunder_tutor.auth import UserId
from blunder_tutor.background.base import BaseJob
from blunder_tutor.background.registry import register_job
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import JobExecutionRequestEvent
from blunder_tutor.fetchers import chesscom, lichess

if TYPE_CHECKING:
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.settings import SettingsRepository
    from blunder_tutor.services.job_service import JobService, ProgressCallback

logger = logging.getLogger(__name__)

_DEFAULT_MAX_GAMES = 1000

_FETCHERS = MappingProxyType({"lichess": lichess.fetch, "chesscom": chesscom.fetch})


@register_job
class ImportGamesJob(BaseJob):
    job_identifier: ClassVar[str] = "import"

    def __init__(
        self,
        job_service: JobService,
        settings_repo: SettingsRepository,
        game_repo: GameRepository,
        user_id: UserId,
        event_bus: EventBus | None = None,
    ) -> None:
        self.job_service = job_service
        self.settings_repo = settings_repo
        self.game_repo = game_repo
        self.user_id = user_id
        self.event_bus = event_bus

    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
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

    async def _import(
        self,
        source: str,
        username: str,
        max_games: int,
        progress: ProgressCallback,
    ) -> dict[str, Any]:
        async def fetcher_progress(current: int, _total: int) -> None:  # noqa: WPS430 — fetcher API expects (current, total); we forward current to our progress(int) shape.
            await progress(current)

        fetcher = _FETCHERS[source]
        games, _ = await fetcher(
            username, max_games, progress_callback=fetcher_progress
        )

        inserted = await self.game_repo.insert_games(games)
        await progress(len(games))
        return {"stored": inserted, "skipped": len(games) - inserted}

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
    if source not in _FETCHERS:
        raise ValueError(f"Unknown source: {source}")
    return source, username
