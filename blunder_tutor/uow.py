from pathlib import Path

from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.puzzle_attempt_repository import PuzzleAttemptRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.repositories.stats_repository import StatsRepository


class UnitOfWork:
    """Unit of Work pattern for managing database transactions and providing access to repositories."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.games = GameRepository(db_path)
        self.jobs = JobRepository(db_path)
        self.puzzle_attempts = PuzzleAttemptRepository(db_path)
        self.stats = StatsRepository(db_path)
        self.settings = SettingsRepository(db_path)
        self.analysis = AnalysisRepository(db_path)
        self.conn = None

    def __enter__(self):
        self.games.bind_connection(self.conn)
        self.jobs.bind_connection(self.conn)
        self.puzzle_attempts.bind_connection(self.conn)
        self.stats.bind_connection(self.conn)
        self.settings.bind_connection(self.conn)
        self.analysis.bind_connection(self.conn)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            raise exc_value
