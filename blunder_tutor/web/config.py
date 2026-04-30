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

AuthMode = Literal["none", "credentials"]

# 64 hex chars = 32 random bytes = the canonical output of
# `secrets.token_hex(32)` / `secrets.token_urlsafe(32)`. We reject anything
# shorter because `SECRET_KEY` is used for HMAC invite codes and future
# CSRF tokens; 128+ bits of entropy is the operational floor.
SECRET_KEY_MIN_LEN = 64

# Session lifetime defaults: 30 days for absolute max, 7 days for idle
# expiry. Values match OWASP "remember-me" guidance for self-hosted apps.
_SECONDS_PER_DAY = 60 * 60 * 24
_SESSION_MAX_AGE_DAYS = 30
_SESSION_IDLE_DAYS = 7
_SESSION_MAX_AGE_DEFAULT = _SECONDS_PER_DAY * _SESSION_MAX_AGE_DAYS
_SESSION_IDLE_DEFAULT = _SECONDS_PER_DAY * _SESSION_IDLE_DAYS

# bcrypt cost ceiling per spec (4 is the floor; 31 is the ceiling, though
# in practice anything past ~14 is too slow for a login path).
_BCRYPT_COST_MAX = 31

_TRUTHY = frozenset(("true", "1", "yes"))
_FALSY = frozenset(("false", "0", "no"))


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
    db_path: Path = DEFAULT_DB_PATH
    template_dir: Path = TEMPLATES_PATH


class AuthConfig(BaseModel):
    mode: AuthMode = "none"
    secret_key: str | None = None
    max_users: int = 1
    session_max_age_seconds: int = _SESSION_MAX_AGE_DEFAULT
    session_idle_seconds: int = _SESSION_IDLE_DEFAULT
    # Tri-state: `None` ⇒ "derive from request scheme + vite_dev" (dev
    # convenience); `True` / `False` ⇒ explicit override for prod
    # deployments behind a TLS-terminating reverse proxy where
    # `request.url.scheme` still reads as `http`.
    cookie_secure: bool | None = None
    # Per-IP rate limits. Defaults match OWASP guidance for "low-risk"
    # self-hosted deployments; tune via env for public instances. Login
    # hits bcrypt on every request so the cap also caps CPU cost.
    login_rate_limit: int = 5
    login_rate_window_seconds: int = 60
    signup_rate_limit: int = 3
    signup_rate_window_seconds: int = 60 * 60
    # Whether to trust ``X-Forwarded-For`` when keying rate limiters.
    # MUST stay ``False`` (default) for direct-to-uvicorn deploys — a
    # trusted proxy header on a publicly-reachable origin lets any
    # client spoof the source IP and get a fresh bucket per forged
    # value, trivially bypassing the rate limit. Set to ``True`` only
    # behind a reverse proxy that overwrites the header (nginx
    # ``proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;``
    # and a trusted upstream).
    trust_proxy: bool = False
    # Bcrypt salt cost factor (rounds). ``None`` defers to the library
    # default — production-grade hardness (currently 12). Operators can
    # tune for their hardware via ``AUTH_BCRYPT_COST``; the test suite
    # forces the bcrypt minimum (4) to keep auth-test wall time bounded.
    # Values outside [4, 31] are rejected by bcrypt itself.
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
    # Host header allowlist passed to Starlette TrustedHostMiddleware.
    # Default `["*"]` accepts any Host header — appropriate for single-
    # tenant self-hosted instances. Shared-vhost or multi-tenant
    # deployments MUST set `ALLOWED_HOSTS=example.com,www.example.com`
    # to prevent Host-header spoofing from defeating the CSRF Origin
    # check.
    allowed_hosts: tuple[str, ...] = ("*",)

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


def _parse_optional_bool(raw: str | None) -> bool | None:
    if raw is None or raw == "":
        return None
    low = raw.lower()
    if low in _TRUTHY:
        return True
    if low in _FALSY:
        return False
    raise ValueError(f"expected boolean-like value, got {raw!r}")


def _build_auth_config(environ: Mapping) -> AuthConfig:
    """Extract auth-related env vars and let AuthConfig validate them."""
    return AuthConfig(
        mode=_parse_auth_mode(environ.get("AUTH_MODE")),
        secret_key=environ.get("SECRET_KEY") or None,
        max_users=_parse_positive_int(environ, "MAX_USERS", 1),
        session_max_age_seconds=_parse_positive_int(
            environ, "SESSION_MAX_AGE_SECONDS", _SESSION_MAX_AGE_DEFAULT
        ),
        session_idle_seconds=_parse_positive_int(
            environ, "SESSION_IDLE_SECONDS", _SESSION_IDLE_DEFAULT
        ),
        cookie_secure=_parse_optional_bool(environ.get("AUTH_COOKIE_SECURE")),
        login_rate_limit=_parse_positive_int(environ, "AUTH_LOGIN_RATE_LIMIT", 5),
        login_rate_window_seconds=_parse_positive_int(
            environ, "AUTH_LOGIN_RATE_WINDOW_SECONDS", 60
        ),
        signup_rate_limit=_parse_positive_int(environ, "AUTH_SIGNUP_RATE_LIMIT", 3),
        signup_rate_window_seconds=_parse_positive_int(
            environ, "AUTH_SIGNUP_RATE_WINDOW_SECONDS", 60 * 60
        ),
        trust_proxy=_parse_bool(environ.get("AUTH_TRUST_PROXY"), default=False),
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
    if allowed_hosts_env:
        allowed_hosts = tuple(
            h.strip() for h in allowed_hosts_env.split(",") if h.strip()
        )
    else:
        allowed_hosts = ("*",)

    cache = CacheConfig(
        enabled=_parse_bool(environ.get("CACHE_ENABLED"), default=True),
        default_ttl=int(environ.get("CACHE_DEFAULT_TTL", "300")),
    )

    return AppConfig(
        data=data,
        allowed_hosts=allowed_hosts,
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
