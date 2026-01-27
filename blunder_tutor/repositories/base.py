import sqlite3
from pathlib import Path
from typing import Self

from blunder_tutor.analysis.db import _connect
from blunder_tutor.web.config import AppConfig


class BaseDbRepository:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = None

    def bind_connection(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @property
    def connection(self) -> sqlite3.Connection:
        if self.conn is None:
            self.conn = _connect(self.db_path)
        return self.conn

    @classmethod
    def from_config(cls, config: AppConfig) -> Self:
        return cls(db_path=config.data.db_path)
