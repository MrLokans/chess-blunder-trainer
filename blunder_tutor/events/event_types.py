from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any

from blunder_tutor.auth import UserId
from blunder_tutor.utils.time import now_iso


class EventType(StrEnum):
    """All event types in the system.

    Member values are part of the metrics-tag contract: the
    ``ws.broadcast.sent`` counter tags broadcasts with ``event_type=<value>``.
    Adding members is fine (bounded growth); introducing dynamically-built
    values (e.g., ``f"job.{kind}"``) would break the cardinality guarantee
    documented in `docs/conventions/observability.md` and must be remapped
    onto a static set before merging.
    """

    JOB_CREATED = "job.created"
    JOB_STATUS_CHANGED = "job.status_changed"
    JOB_PROGRESS_UPDATED = "job.progress_updated"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_EXECUTION_REQUESTED = "job.execution_requested"
    STATS_UPDATED = "stats.updated"
    TRAPS_UPDATED = "traps.updated"
    TRAINING_UPDATED = "training.updated"
    CACHE_INVALIDATED = "cache.invalidated"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    timestamp: str

    @classmethod
    def create(cls, event_type: EventType, data: dict[str, Any]) -> "Event":
        return cls(type=event_type, data=data, timestamp=now_iso())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class JobEvent(Event):
    @classmethod
    def create_status_changed(
        cls, job_id: str, job_type: str, status: str, error_message: str | None = None
    ) -> "JobEvent":
        return cls(
            type=EventType.JOB_STATUS_CHANGED,
            data={
                "job_id": job_id,
                "job_type": job_type,
                "status": status,
                "error_message": error_message,
            },
            timestamp=now_iso(),
        )

    @classmethod
    def create_progress_updated(
        cls, job_id: str, job_type: str, current: int, total: int
    ) -> "JobEvent":
        percent = int((current / total) * 100) if total > 0 else 0
        return cls(
            type=EventType.JOB_PROGRESS_UPDATED,
            data={
                "job_id": job_id,
                "job_type": job_type,
                "current": current,
                "total": total,
                "percent": percent,
            },
            timestamp=now_iso(),
        )


@dataclass
class ProgressEvent(Event):
    """Progress update for a long-running job."""


@dataclass
class StatsEvent(Event):
    @classmethod
    def create_stats_updated(cls, user_key: str = "default") -> "StatsEvent":
        return cls(
            type=EventType.STATS_UPDATED,
            data={"trigger": "job_completed", "user_key": user_key},
            timestamp=now_iso(),
        )


@dataclass
class TrapsEvent(Event):
    @classmethod
    def create_traps_updated(cls, user_key: str) -> "TrapsEvent":
        return cls(
            type=EventType.TRAPS_UPDATED,
            data={"trigger": "trap_detection_completed", "user_key": user_key},
            timestamp=now_iso(),
        )


@dataclass
class TrainingEvent(Event):
    @classmethod
    def create_training_updated(cls, user_key: str) -> "TrainingEvent":
        return cls(
            type=EventType.TRAINING_UPDATED,
            data={"trigger": "puzzle_attempt", "user_key": user_key},
            timestamp=now_iso(),
        )


@dataclass
class CacheEvent(Event):
    @classmethod
    def create_cache_invalidated(cls, tags: list[str]) -> "CacheEvent":
        return cls(
            type=EventType.CACHE_INVALIDATED,
            data={"tags": tags},
            timestamp=now_iso(),
        )


@dataclass
class JobExecutionRequestEvent(Event):
    @classmethod
    def create(
        cls,
        job_id: str,
        job_type: str,
        user_id: UserId,
        **kwargs: Any,
    ) -> "JobExecutionRequestEvent":
        return cls(
            type=EventType.JOB_EXECUTION_REQUESTED,
            data={
                "job_id": job_id,
                "job_type": job_type,
                "user_id": user_id,
                "kwargs": kwargs,
            },
            timestamp=now_iso(),
        )
