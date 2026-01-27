"""Base class for background jobs.

This module defines the abstract base class for all background jobs,
providing a consistent interface for job execution with dependency injection.
"""

from __future__ import annotations

import abc
from typing import Any, ClassVar


class BaseJob(abc.ABC):
    """Abstract base class for background jobs.

    All job classes should inherit from this class and implement the execute method.
    Jobs receive their dependencies via __init__ and are executed by calling execute()
    with the job_id and any additional keyword arguments.
    """

    job_identifier: ClassVar[str]

    @abc.abstractmethod
    async def execute(self, job_id: str, **kwargs: Any) -> dict[str, Any]:
        """Execute the job.

        Args:
            job_id: The unique identifier for this job instance.
            **kwargs: Additional job-specific arguments.

        Returns:
            A dictionary containing the job result.
        """
        ...
