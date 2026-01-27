from __future__ import annotations

import argparse
import typing
from pathlib import Path

from pydantic import BaseModel

from blunder_tutor import constants


class DataConfig(BaseModel):
    db_path: Path = constants.DEFAULT_DB_PATH
    template_dir: Path = constants.TEMPLATES_PATH


class EngineConfig(BaseModel):
    path: str
    depth: int = constants.DEFAULT_ENGINE_DEPTH
    time_limit: float = constants.DEFAULT_ENGINE_TIME_LIMIT


class AppConfig(BaseModel):
    username: str | None = None
    engine_path: str
    engine: EngineConfig
    data: DataConfig = DataConfig()


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
    return AppConfig(
        data=DataConfig(),
        engine_path=final_engine_path,
        engine=EngineConfig(
            path=final_engine_path,
        ),
    )
