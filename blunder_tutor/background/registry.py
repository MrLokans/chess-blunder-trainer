from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from blunder_tutor.background.base import BaseJob

_JOB_REGISTRY: dict[str, type[BaseJob]] = {}  # noqa: WPS407 — populated by `@register_job` at import time; intentionally mutable.


def register_job(job_class: type[BaseJob]) -> type[BaseJob]:
    identifier = job_class.job_identifier
    if identifier in _JOB_REGISTRY:
        raise ValueError(f"Job identifier '{identifier}' is already registered")
    _JOB_REGISTRY[identifier] = job_class
    return job_class


def get_job_class(job_identifier: str) -> type[BaseJob] | None:
    return _JOB_REGISTRY.get(job_identifier)


def get_all_job_classes() -> dict[str, type[BaseJob]]:
    return _JOB_REGISTRY.copy()
