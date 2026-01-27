from __future__ import annotations

import argparse
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


def config_factory(parsed_args: argparse.Namespace, environ: dict) -> AppConfig:
    default_stockfish = None
    for path in [
        "/usr/games/stockfish",
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
    ]:
        if Path(path).exists():
            default_stockfish = path
            break
    engine_path = environ.get("STOCKFISH_BINARY", default_stockfish)
    final_engine_path = parsed_args and parsed_args.engine_path or engine_path

    return AppConfig(
        data=DataConfig(),
        depth=parsed_args
        and getattr(parsed_args, "depth", None)
        or constants.DEFAULT_ENGINE_DEPTH,
        engine_path=final_engine_path,
        engine=EngineConfig(
            path=final_engine_path,
        ),
    )
