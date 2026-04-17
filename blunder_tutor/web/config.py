from __future__ import annotations

import argparse
import typing
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, model_validator

from blunder_tutor import constants
from blunder_tutor.cache.config import CacheConfig

AuthMode = Literal["none", "credentials"]

# 64 hex chars = 32 random bytes = the canonical output of
# `secrets.token_hex(32)` / `secrets.token_urlsafe(32)`. We reject anything
# shorter because `SECRET_KEY` is used for HMAC invite codes and future
# CSRF tokens; 128+ bits of entropy is the operational floor.
SECRET_KEY_MIN_LEN = 64

_TRUTHY = frozenset({"true", "1", "yes"})
_FALSY = frozenset({"false", "0", "no"})


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None or raw == "":
        return default
    low = raw.lower()
    if low in _TRUTHY:
        return True
    if low in _FALSY:
        return False
    raise ValueError(f"expected boolean-like value, got {raw!r}")


class DataConfig(BaseModel):
    db_path: Path = constants.DEFAULT_DB_PATH
    template_dir: Path = constants.TEMPLATES_PATH


class AuthConfig(BaseModel):
    mode: AuthMode = "none"
    secret_key: str | None = None
    max_users: int = 1
    session_max_age_seconds: int = 60 * 60 * 24 * 30
    session_idle_seconds: int = 60 * 60 * 24 * 7

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        if self.max_users < 1:
            raise ValueError(f"MAX_USERS must be >= 1, got {self.max_users}")
        if self.session_max_age_seconds < 1:
            raise ValueError(
                f"SESSION_MAX_AGE_SECONDS must be >= 1, got {self.session_max_age_seconds}"
            )
        if self.session_idle_seconds < 1:
            raise ValueError(
                f"SESSION_IDLE_SECONDS must be >= 1, got {self.session_idle_seconds}"
            )
        if self.session_idle_seconds > self.session_max_age_seconds:
            raise ValueError(
                "SESSION_IDLE_SECONDS must be <= SESSION_MAX_AGE_SECONDS "
                f"({self.session_idle_seconds} > {self.session_max_age_seconds})"
            )
        if self.mode == "credentials":
            if not self.secret_key:
                raise ValueError(
                    "SECRET_KEY env var is required when AUTH_MODE=credentials"
                )
            if len(self.secret_key) < SECRET_KEY_MIN_LEN:
                raise ValueError(
                    f"SECRET_KEY must be at least {SECRET_KEY_MIN_LEN} chars "
                    f"when AUTH_MODE=credentials (got {len(self.secret_key)})"
                )
        return self


class EngineConfig(BaseModel):
    path: str
    depth: int = constants.DEFAULT_ENGINE_DEPTH
    time_limit: float = constants.DEFAULT_ENGINE_TIME_LIMIT


class ThrottleConfig(BaseModel):
    engine_requests: int = 10
    engine_window_seconds: int = 60


class AnalyticsConfig(BaseModel):
    plausible_domain: str | None = None
    plausible_script_url: str = "https://plausible.io/js/script.js"

    @property
    def enabled(self) -> bool:
        return self.plausible_domain is not None


class AppConfig(BaseModel):
    username: str | None = None
    engine_path: str
    engine: EngineConfig
    data: DataConfig = DataConfig()
    demo_mode: bool = False
    vite_dev: bool = False
    throttle: ThrottleConfig = ThrottleConfig()
    analytics: AnalyticsConfig = AnalyticsConfig()
    cache: CacheConfig = CacheConfig()
    auth: AuthConfig = AuthConfig()

    @model_validator(mode="after")
    def _check_mode_compatibility(self) -> Self:
        if self.demo_mode and self.auth.mode == "credentials":
            raise ValueError("DEMO_MODE cannot be combined with AUTH_MODE=credentials")
        return self


def _parse_positive_int(environ: typing.Mapping, key: str, default: int) -> int:
    raw = environ.get(key)
    if raw is None:
        return default
    if raw == "":
        raise ValueError(
            f"{key} is set to an empty string; unset it to use the default"
        )
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be a positive integer, got {raw!r}") from exc
    if value < 1:
        raise ValueError(f"{key} must be >= 1, got {value}")
    return value


def _parse_auth_mode(raw: str | None) -> AuthMode:
    mode_raw = (raw or "").strip().lower()
    if mode_raw in ("", "none"):
        return "none"
    if mode_raw == "credentials":
        return "credentials"
    raise ValueError(f"AUTH_MODE must be 'none' or 'credentials', got {mode_raw!r}")


def _build_auth_config(environ: typing.Mapping) -> AuthConfig:
    """Extract auth-related env vars and let AuthConfig validate them."""
    return AuthConfig(
        mode=_parse_auth_mode(environ.get("AUTH_MODE")),
        secret_key=environ.get("SECRET_KEY") or None,
        max_users=_parse_positive_int(environ, "MAX_USERS", 1),
        session_max_age_seconds=_parse_positive_int(
            environ, "SESSION_MAX_AGE_SECONDS", 60 * 60 * 24 * 30
        ),
        session_idle_seconds=_parse_positive_int(
            environ, "SESSION_IDLE_SECONDS", 60 * 60 * 24 * 7
        ),
    )


def get_engine_path(environ: typing.Mapping) -> str:
    engine_path = environ.get("STOCKFISH_BINARY")
    if engine_path is not None:
        return engine_path
    for path in (
        "/usr/games/stockfish",
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
    ):
        if Path(path).exists():
            return path
    raise ValueError(
        "Unable to resolve the stockfish binary path. Make sure the `STOCKFISH_BINARY` env variable is set."
    )


def config_factory(
    parsed_args: argparse.Namespace, environ: typing.Mapping
) -> AppConfig:
    final_engine_path = (
        parsed_args and parsed_args.engine_path or get_engine_path(environ)
    )
    throttle = ThrottleConfig()
    throttle_env = environ.get("DEMO_THROTTLE_RATE")
    if throttle_env:
        parts = throttle_env.split("/", 1)
        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
            throttle = ThrottleConfig(
                engine_requests=int(parts[0]),
                engine_window_seconds=int(parts[1]),
            )

    db_path_env = environ.get("DB_PATH")
    data = DataConfig(db_path=Path(db_path_env)) if db_path_env else DataConfig()

    cache = CacheConfig(
        enabled=_parse_bool(environ.get("CACHE_ENABLED"), default=True),
        default_ttl=int(environ.get("CACHE_DEFAULT_TTL", "300")),
    )

    return AppConfig(
        data=data,
        engine_path=final_engine_path,
        engine=EngineConfig(
            path=final_engine_path,
        ),
        demo_mode=_parse_bool(environ.get("DEMO_MODE"), default=False),
        vite_dev=_parse_bool(environ.get("VITE_DEV"), default=False),
        throttle=throttle,
        analytics=AnalyticsConfig(
            plausible_domain=environ.get("PLAUSIBLE_DOMAIN"),
            plausible_script_url=environ.get(
                "PLAUSIBLE_SCRIPT_URL", "https://plausible.io/js/script.js"
            ),
        ),
        cache=cache,
        auth=_build_auth_config(environ),
    )
