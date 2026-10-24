from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.httpx2 import Httpx2Integration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from blunder_tutor.observability.config import ObservabilityConfig
from blunder_tutor.observability.scrubbing import make_event_scrubber

# Healthchecks and static assets are noise; add new noise here, not in external config.
_NOISE_PATHS = frozenset(("/health", "/favicon.ico"))
_NOISE_PREFIXES = ("/static",)

# Cap so a stuck Sentry connection can't hang shutdown; dropping the tail beats hanging.
_FLUSH_TIMEOUT_SECONDS = 2.0

# Single activation flag read by `metrics` and `tracing`.
active: bool = False


def _set_active(value: bool) -> None:
    global active  # noqa: PLW0603 — module-level singleton, configured once at app boot.
    active = value


def _traces_sampler(
    sampling_context: dict[str, Any],
    *,
    configured_rate: float,
    trace_health: bool,
) -> float:
    if not trace_health:
        asgi_scope = sampling_context.get("asgi_scope") or {}
        path = asgi_scope.get("path", "")
        if path in _NOISE_PATHS or path.startswith(_NOISE_PREFIXES):
            return 0.0
    # Honor the parent's decision both ways; the spec's `or` shortcut would up-sample on
    # parent_sampled=False.
    parent_sampled = sampling_context.get("parent_sampled")
    if parent_sampled is not None:
        return float(parent_sampled)
    return configured_rate


def _build_traces_sampler(
    configured_rate: float,
    trace_health: bool,
) -> Callable[[dict[str, Any]], float]:
    return functools.partial(
        _traces_sampler,
        configured_rate=configured_rate,
        trace_health=trace_health,
    )


def _build_integrations() -> list[Any]:
    return [
        FastApiIntegration(),
        StarletteIntegration(),
        Httpx2Integration(),
        AsyncioIntegration(),
        LoggingIntegration(),
    ]


def init_observability(config: ObservabilityConfig) -> None:
    if active or not config.enabled:
        return

    sentry_sdk.init(
        dsn=config.sentry_dsn,
        environment=config.sentry_environment,
        release=config.sentry_release,
        traces_sample_rate=config.traces_sample_rate,
        traces_sampler=_build_traces_sampler(
            config.traces_sample_rate,
            config.trace_health_endpoint,
        ),
        send_default_pii=config.send_default_pii,
        event_scrubber=make_event_scrubber(),
        integrations=_build_integrations(),
    )

    _set_active(True)


def shutdown_observability() -> None:
    if not active:
        return
    sentry_sdk.flush(timeout=_FLUSH_TIMEOUT_SECONDS)
    _set_active(False)
