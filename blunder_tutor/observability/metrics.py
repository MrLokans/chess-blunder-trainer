from __future__ import annotations

import sentry_sdk

from blunder_tutor.observability import sentry_init


def count(
    name: str,
    value: float = 1.0,
    tags: dict[str, str] | None = None,
) -> None:
    if not sentry_init.active:
        return
    sentry_sdk.metrics.count(name, value, attributes=tags)


def gauge(
    name: str,
    value: float,
    tags: dict[str, str] | None = None,
) -> None:
    if not sentry_init.active:
        return
    sentry_sdk.metrics.gauge(name, value, attributes=tags)


def distribution(
    name: str,
    value: float,
    tags: dict[str, str] | None = None,
) -> None:
    if not sentry_init.active:
        return
    sentry_sdk.metrics.distribution(name, value, attributes=tags)
