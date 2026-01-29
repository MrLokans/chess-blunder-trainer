from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    """All event types in the system."""

    JOB_CREATED = "job.created"
    JOB_STATUS_CHANGED = "job.status_changed"
    JOB_PROGRESS_UPDATED = "job.progress_updated"
    JOB_COMPLETED = "job.completed"
    JOB_FAILED = "job.failed"
    JOB_EXECUTION_REQUESTED = "job.execution_requested"
    STATS_UPDATED = "stats.updated"


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
    pass


@dataclass
class StatsEvent(Event):
    @classmethod
    def create_stats_updated(cls) -> "StatsEvent":
        return cls(
            type=EventType.STATS_UPDATED,
            data={"trigger": "job_completed"},
            timestamp=datetime.utcnow().isoformat(),
        )


@dataclass
class JobExecutionRequestEvent(Event):
    @classmethod
    def create(
        cls,
        job_id: str,
        job_type: str,
        **kwargs: Any,
    ) -> "JobExecutionRequestEvent":
        return cls(
            type=EventType.JOB_EXECUTION_REQUESTED,
            data={
                "job_id": job_id,
                "job_type": job_type,
                "kwargs": kwargs,
            },
            timestamp=datetime.utcnow().isoformat(),
        )
