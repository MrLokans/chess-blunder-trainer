from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from blunder_tutor.auth import UserId


class EventType(str, Enum):
    """All event types in the system."""

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
        return cls(type=event_type, data=data, timestamp=datetime.utcnow().isoformat())

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
            timestamp=datetime.utcnow().isoformat(),
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
            timestamp=datetime.utcnow().isoformat(),
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
            timestamp=datetime.utcnow().isoformat(),
        )


@dataclass
class TrapsEvent(Event):
    @classmethod
    def create_traps_updated(cls, user_key: str) -> "TrapsEvent":
        return cls(
            type=EventType.TRAPS_UPDATED,
            data={"trigger": "trap_detection_completed", "user_key": user_key},
            timestamp=datetime.utcnow().isoformat(),
        )


@dataclass
class TrainingEvent(Event):
    @classmethod
    def create_training_updated(cls, user_key: str) -> "TrainingEvent":
        return cls(
            type=EventType.TRAINING_UPDATED,
            data={"trigger": "puzzle_attempt", "user_key": user_key},
            timestamp=datetime.utcnow().isoformat(),
        )


@dataclass
class CacheEvent(Event):
    @classmethod
    def create_cache_invalidated(cls, tags: list[str]) -> "CacheEvent":
        return cls(
            type=EventType.CACHE_INVALIDATED,
            data={"tags": tags},
            timestamp=datetime.utcnow().isoformat(),
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
            timestamp=datetime.utcnow().isoformat(),
        )
