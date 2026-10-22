from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, model_validator

from blunder_tutor.cache.config import CacheConfig
from blunder_tutor.constants import (
    AUTH_MODE_CREDENTIALS,
    AUTH_MODE_NONE,
    DEFAULT_DB_PATH,
    DEFAULT_ENGINE_DEPTH,
    DEFAULT_ENGINE_TIME_LIMIT,
    TEMPLATES_PATH,
)
from blunder_tutor.observability.config import (
    ObservabilityConfig,
    build_observability_config,
)
from blunder_tutor.utils.env import parse_bool, parse_optional_bool

AuthMode = Literal["none", "credentials"]

# 64 hex chars = 32 bytes; `SECRET_KEY` signs invite codes, so shorter is rejected (128+
# bits is the floor).
SECRET_KEY_MIN_LEN = 64

# 30 days absolute / 7 days idle, per OWASP remember-me guidance.
_SECONDS_PER_DAY = 60 * 60 * 24
_SESSION_MAX_AGE_DAYS = 30
_SESSION_IDLE_DAYS = 7
_SESSION_MAX_AGE_DEFAULT = _SECONDS_PER_DAY * _SESSION_MAX_AGE_DAYS
_SESSION_IDLE_DEFAULT = _SECONDS_PER_DAY * _SESSION_IDLE_DAYS

# bcrypt's range is 4-31; past ~14 is too slow for a login path.
_BCRYPT_COST_MAX = 31


class DataConfig(BaseModel):
    db_path: Path = DEFAULT_DB_PATH
    template_dir: Path = TEMPLATES_PATH


class AuthConfig(BaseModel):
    mode: AuthMode = "none"
    secret_key: str | None = None
    max_users: int = 1
    session_max_age_seconds: int = _SESSION_MAX_AGE_DEFAULT
    session_idle_seconds: int = _SESSION_IDLE_DEFAULT
    # `None` derives from request scheme + vite_dev; explicit True/False for prod behind
    # a TLS-terminating proxy where the scheme still reads `http`.
    cookie_secure: bool | None = None
    # OWASP low-risk defaults; login hits bcrypt per request, so this also caps CPU.
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60
    signup_rate_limit: int = 3
    signup_rate_window_seconds: int = 60 * 60
    # Must stay False for direct-to-uvicorn: a trusted `X-Forwarded-For` lets clients
    # spoof IPs and dodge the limiter. True only behind a proxy that overwrites the
    # header.
    trust_proxy: bool = False
    # `None` uses the library default (12). Tests force the minimum (4) to keep auth
    # tests fast.
    bcrypt_cost: int | None = None

    @model_validator(mode="after")
    def _check_invariants(self) -> Self:
        if self.max_users < 1:
            raise ValueError(f"MAX_USERS must be >= 1, got {self.max_users}")
        if (
            self.bcrypt_cost is not None
            and not 4 <= self.bcrypt_cost <= _BCRYPT_COST_MAX
        ):
            raise ValueError(
                f"AUTH_BCRYPT_COST must be between 4 and 31, got {self.bcrypt_cost}"
            )
        self._validate_sessions()
        self._validate_secret_key()
        return self

    def _validate_sessions(self) -> None:
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

    def _validate_secret_key(self) -> None:
        if self.mode != AUTH_MODE_CREDENTIALS:
            return
        if not self.secret_key:
            raise ValueError(
                "SECRET_KEY env var is required when AUTH_MODE=credentials"
            )
        if len(self.secret_key) < SECRET_KEY_MIN_LEN:
            raise ValueError(
                f"SECRET_KEY must be at least {SECRET_KEY_MIN_LEN} chars "
                f"when AUTH_MODE=credentials (got {len(self.secret_key)})"
            )


class EngineConfig(BaseModel):
    path: str
    depth: int = DEFAULT_ENGINE_DEPTH
    time_limit: float = DEFAULT_ENGINE_TIME_LIMIT


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
    observability: ObservabilityConfig = ObservabilityConfig()
    # None (the env default when `ALLOWED_HOSTS` is unset) means: in no-login, non-demo
    # mode only localhost and IP literals, which blocks DNS rebinding; elsewhere any
    # Host. Shared-vhost deploys must set `ALLOWED_HOSTS`, or a spoofed Host defeats the
    # CSRF Origin check.
    allowed_hosts: tuple[str, ...] | None = ("*",)

    @model_validator(mode="after")
    def _check_mode_compatibility(self) -> Self:
        if self.demo_mode and self.auth.mode == AUTH_MODE_CREDENTIALS:
            raise ValueError("DEMO_MODE cannot be combined with AUTH_MODE=credentials")
        return self


def _parse_positive_int(environ: Mapping, key: str, default: int) -> int:
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
    if mode_raw in ("", AUTH_MODE_NONE):
        return AUTH_MODE_NONE
    if mode_raw == AUTH_MODE_CREDENTIALS:
        return AUTH_MODE_CREDENTIALS
    raise ValueError(f"AUTH_MODE must be 'none' or 'credentials', got {mode_raw!r}")


def _build_auth_config(environ: Mapping) -> AuthConfig:
    return AuthConfig(
        mode=_parse_auth_mode(environ.get("AUTH_MODE")),
        secret_key=(environ.get("SECRET_KEY") or "").strip() or None,
        max_users=_parse_positive_int(environ, "MAX_USERS", 1),
        session_max_age_seconds=_parse_positive_int(
            environ, "SESSION_MAX_AGE_SECONDS", _SESSION_MAX_AGE_DEFAULT
        ),
        session_idle_seconds=_parse_positive_int(
            environ, "SESSION_IDLE_SECONDS", _SESSION_IDLE_DEFAULT
        ),
        cookie_secure=parse_optional_bool(environ.get("AUTH_COOKIE_SECURE")),
        login_rate_limit=_parse_positive_int(environ, "AUTH_LOGIN_RATE_LIMIT", 5),
        login_rate_window_seconds=_parse_positive_int(
            environ, "AUTH_LOGIN_RATE_WINDOW_SECONDS", 60
        ),
        signup_rate_limit=_parse_positive_int(environ, "AUTH_SIGNUP_RATE_LIMIT", 3),
        signup_rate_window_seconds=_parse_positive_int(
            environ, "AUTH_SIGNUP_RATE_WINDOW_SECONDS", 60 * 60
        ),
        trust_proxy=parse_bool(environ.get("AUTH_TRUST_PROXY"), default=False),
        bcrypt_cost=_parse_optional_positive_int(environ.get("AUTH_BCRYPT_COST")),
    )


def _parse_optional_positive_int(raw: str | None) -> int | None:
    if raw is None or raw == "":
        return None
    value = int(raw)
    if value < 1:
        raise ValueError(f"expected a positive integer, got {raw!r}")
    return value


def get_engine_path(environ: Mapping) -> str:
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


def config_factory(parsed_args: argparse.Namespace, environ: Mapping) -> AppConfig:
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

    allowed_hosts_env = environ.get("ALLOWED_HOSTS")
    allowed_hosts = None
    if allowed_hosts_env:
        allowed_hosts = tuple(
            h.strip() for h in allowed_hosts_env.split(",") if h.strip()
        )

    cache = CacheConfig(
        enabled=parse_bool(environ.get("CACHE_ENABLED"), default=True),
        default_ttl=int(environ.get("CACHE_DEFAULT_TTL", "300")),
    )

    return AppConfig(
        data=data,
        allowed_hosts=allowed_hosts,
        engine_path=final_engine_path,
        engine=EngineConfig(
            path=final_engine_path,
        ),
        demo_mode=parse_bool(environ.get("DEMO_MODE"), default=False),
        vite_dev=parse_bool(environ.get("VITE_DEV"), default=False),
        throttle=throttle,
        analytics=AnalyticsConfig(
            plausible_domain=environ.get("PLAUSIBLE_DOMAIN"),
            plausible_script_url=environ.get(
                "PLAUSIBLE_SCRIPT_URL", "https://plausible.io/js/script.js"
            ),
        ),
        cache=cache,
        auth=_build_auth_config(environ),
        observability=build_observability_config(environ),
    )
