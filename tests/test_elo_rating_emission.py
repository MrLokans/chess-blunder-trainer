from __future__ import annotations

import asyncio
import sqlite3
from contextlib import closing
from http import HTTPStatus
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from blunder_tutor.constants import (
    JOB_STATUS_COMPLETED,
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
)
from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.events.event_types import EventType
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.profile import SqliteProfileRepository
from blunder_tutor.services.job_service import JobService


def _drain_until_match(queue: asyncio.Queue, *, expected: int, timeout: float = 1.0):
    async def _collect():
        events = []
        while len(events) < expected:
            ev = await asyncio.wait_for(queue.get(), timeout=timeout)
            if ev.type == EventType.ELO_RATING_UPDATED:
                events.append(ev)
        return events

    return _collect()


class TestJobServiceEmitsEloRating:
    @pytest.fixture
    async def event_bus(self) -> EventBus:
        return EventBus()

    @pytest.fixture
    async def job_repo(self, db_path: Path):
        repo = JobRepository(db_path)
        try:
            yield repo
        finally:
            await repo.close()

    @pytest.fixture
    async def service(self, job_repo: JobRepository, event_bus: EventBus) -> JobService:
        return JobService(job_repository=job_repo, event_bus=event_bus)

    async def test_complete_job_publishes_elo_rating_updated(
        self,
        service: JobService,
        event_bus: EventBus,
    ) -> None:
        observer = await event_bus.subscribe(EventType.ELO_RATING_UPDATED)
        job_id = await service.create_job(job_type="import", username="alice")

        await service.complete_job(job_id, result={"games": 0})

        events = await asyncio.wait_for(
            _drain_until_match(observer, expected=1), timeout=1.0
        )
        assert events[0].data["user_key"] == "alice"
        assert events[0].data["trigger"] == "game_sync_completed"

    async def test_status_completed_publishes_elo_rating_updated(
        self,
        service: JobService,
        event_bus: EventBus,
    ) -> None:
        observer = await event_bus.subscribe(EventType.ELO_RATING_UPDATED)
        job_id = await service.create_job(job_type="import", username="bob")

        # Status transition from running → completed (independent of complete_job).
        await service.update_job_status(job_id, JOB_STATUS_RUNNING)
        await service.update_job_status(job_id, JOB_STATUS_COMPLETED)

        events = await asyncio.wait_for(
            _drain_until_match(observer, expected=1), timeout=1.0
        )
        assert events[0].data["user_key"] == "bob"

    async def test_pending_status_does_not_publish(
        self,
        service: JobService,
        event_bus: EventBus,
    ) -> None:
        observer = await event_bus.subscribe(EventType.ELO_RATING_UPDATED)
        await service.create_job(job_type="import", username="charlie")

        # Creating a job goes through PENDING status → no ELO event expected.
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(observer.get(), timeout=0.1)
        assert JOB_STATUS_PENDING == "pending"

    async def test_non_game_job_completion_does_not_publish(
        self,
        service: JobService,
        event_bus: EventBus,
    ) -> None:
        # `analyze` doesn't touch game_index_cache rows; rating-history
        # cache should not be invalidated when an analyze job finishes.
        observer = await event_bus.subscribe(EventType.ELO_RATING_UPDATED)
        job_id = await service.create_job(job_type="analyze", username="dana")

        await service.complete_job(job_id, result={"games": 0})

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(observer.get(), timeout=0.1)


class TestProfileDeleteEmitsEloRating:
    def _insert_game_for(self, db_path: Path, *, profile_id: int) -> None:
        with closing(sqlite3.connect(str(db_path))) as conn:
            conn.execute(
                "INSERT INTO game_index_cache "
                "(game_id, source, username, pgn_content, "
                " indexed_at, profile_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                ("g1", "lichess", "alice", "1.e4 e5", "2026-04-30", profile_id),
            )
            conn.commit()

    async def _capture_elo_event(
        self, app: TestClient, *, profile_id: int, detach: str
    ):
        event_bus: EventBus = app.app.state.event_bus
        observer = await event_bus.subscribe(EventType.ELO_RATING_UPDATED)

        response = app.delete(f"/api/profiles/{profile_id}?detach_games={detach}")
        assert response.status_code == HTTPStatus.NO_CONTENT
        return await asyncio.wait_for(observer.get(), timeout=1.0)

    async def test_detach_true_emits_elo_rating_updated(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")
        self._insert_game_for(db_path, profile_id=profile.id)

        event = await self._capture_elo_event(app, profile_id=profile.id, detach="true")
        assert event.type == EventType.ELO_RATING_UPDATED
        assert event.data["trigger"] == "profile_deleted"

    async def test_detach_false_emits_elo_rating_updated(
        self, app: TestClient, db_path: Path
    ) -> None:
        async with SqliteProfileRepository(db_path) as repo:
            profile = await repo.create("lichess", "alice")
        self._insert_game_for(db_path, profile_id=profile.id)

        event = await self._capture_elo_event(
            app, profile_id=profile.id, detach="false"
        )
        assert event.type == EventType.ELO_RATING_UPDATED
        assert event.data["trigger"] == "profile_deleted"

    async def test_404_does_not_emit_event(self, app: TestClient) -> None:
        event_bus: EventBus = app.app.state.event_bus
        observer = await event_bus.subscribe(EventType.ELO_RATING_UPDATED)

        response = app.delete("/api/profiles/9999?detach_games=true")
        assert response.status_code == HTTPStatus.NOT_FOUND

        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(observer.get(), timeout=0.1)
