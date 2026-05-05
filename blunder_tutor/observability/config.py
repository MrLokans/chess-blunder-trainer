from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Self

from pydantic import BaseModel, Field, model_validator

from blunder_tutor.utils.env import parse_bool


def _parse_rate(raw: str | None, *, default: float) -> float:
    if raw is None or raw == "":
        return default
    return float(raw)


class ObservabilityConfig(BaseModel):
    sentry_enabled: bool = False
    sentry_dsn: str | None = None
    sentry_environment: str = "production"
    sentry_release: str | None = None
    traces_sample_rate: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    send_default_pii: bool = False
    trace_health_endpoint: bool = False

    @property
    def enabled(self) -> bool:
        return self.sentry_enabled and self.sentry_dsn is not None

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        if self.sentry_enabled and not self.sentry_dsn:
            raise ValueError(
                "SENTRY_ENABLED=true requires SENTRY_DSN to be set",
            )
        return self


def build_observability_config(environ: Mapping) -> ObservabilityConfig:
    return ObservabilityConfig(
        sentry_enabled=parse_bool(environ.get("SENTRY_ENABLED"), default=False),
        sentry_dsn=(environ.get("SENTRY_DSN") or "").strip() or None,
        sentry_environment=environ.get("SENTRY_ENVIRONMENT", "dev"),
        sentry_release=(environ.get("SENTRY_RELEASE") or "").strip() or None,
        traces_sample_rate=_parse_rate(
            environ.get("SENTRY_TRACES_SAMPLE_RATE"), default=1.0
        ),
        send_default_pii=parse_bool(
            environ.get("SENTRY_SEND_DEFAULT_PII"), default=False
        ),
        trace_health_endpoint=parse_bool(
            environ.get("SENTRY_TRACE_HEALTH"), default=False
        ),
    )
