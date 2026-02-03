"""Background job classes.

This package contains class-based job implementations for background tasks.
"""

from blunder_tutor.background.jobs.analyze_games import AnalyzeGamesJob
from blunder_tutor.background.jobs.backfill_eco import BackfillECOJob
from blunder_tutor.background.jobs.backfill_phases import BackfillPhasesJob
from blunder_tutor.background.jobs.delete_all_data import DeleteAllDataJob
from blunder_tutor.background.jobs.import_games import ImportGamesJob
from blunder_tutor.background.jobs.sync_games import SyncGamesJob

__all__ = [
    "AnalyzeGamesJob",
    "BackfillECOJob",
    "BackfillPhasesJob",
    "DeleteAllDataJob",
    "ImportGamesJob",
    "SyncGamesJob",
]
