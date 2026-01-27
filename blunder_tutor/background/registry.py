"""Job registry for background jobs.

This module provides a registry for job classes, allowing jobs to be
looked up by their identifier at runtime.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blunder_tutor.background.base import BaseJob

_JOB_REGISTRY: dict[str, type[BaseJob]] = {}


def register_job(job_class: type[BaseJob]) -> type[BaseJob]:
    """Decorator to register a job class in the global registry.

    Args:
        job_class: The job class to register.

    Returns:
        The job class (unmodified).

    Raises:
        ValueError: If the job_identifier is already registered.
    """
    identifier = job_class.job_identifier
    if identifier in _JOB_REGISTRY:
        raise ValueError(f"Job identifier '{identifier}' is already registered")
    _JOB_REGISTRY[identifier] = job_class
    return job_class


def get_job_class(job_identifier: str) -> type[BaseJob] | None:
    """Get a job class by its identifier.

    Args:
        job_identifier: The job identifier to look up.

    Returns:
        The job class if found, None otherwise.
    """
    return _JOB_REGISTRY.get(job_identifier)


def get_all_job_classes() -> dict[str, type[BaseJob]]:
    """Get all registered job classes.

    Returns:
        A dictionary mapping job identifiers to job classes.
    """
    return _JOB_REGISTRY.copy()
