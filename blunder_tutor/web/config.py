from __future__ import annotations

import argparse
import typing
from pathlib import Path

from pydantic import BaseModel

from blunder_tutor import constants
from blunder_tutor.cache.config import CacheConfig


class DataConfig(BaseModel):
    db_path: Path = constants.DEFAULT_DB_PATH
    template_dir: Path = constants.TEMPLATES_PATH


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
    (
        parsed_args
        and getattr(parsed_args, "depth", None)
        or constants.DEFAULT_ENGINE_DEPTH
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
        enabled=environ.get("CACHE_ENABLED", "true").lower()
        not in ("false", "0", "no"),
        default_ttl=int(environ.get("CACHE_DEFAULT_TTL", "300")),
    )

    return AppConfig(
        data=data,
        engine_path=final_engine_path,
        engine=EngineConfig(
            path=final_engine_path,
        ),
        demo_mode=environ.get("DEMO_MODE", "").lower() in ("true", "1", "yes"),
        vite_dev=environ.get("VITE_DEV", "").lower() in ("true", "1", "yes"),
        throttle=throttle,
        analytics=AnalyticsConfig(
            plausible_domain=environ.get("PLAUSIBLE_DOMAIN"),
            plausible_script_url=environ.get(
                "PLAUSIBLE_SCRIPT_URL", "https://plausible.io/js/script.js"
            ),
        ),
        cache=cache,
    )
