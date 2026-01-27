from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from blunder_tutor.events.event_bus import EventBus
from blunder_tutor.repositories.job_repository import JobRepository
from blunder_tutor.repositories.settings import SettingsRepository
from blunder_tutor.services.job_service import JobService

logger = logging.getLogger(__name__)


# FIXME: Jobs are a mess, because they completely ignore the DI and FastAPI
# is not very well designed in terms of re-using the DI component


def _create_job_service(data_dir: Path, event_bus: EventBus | None) -> JobService:
    """Create a JobService with its dependencies."""
    db_path = data_dir / "main.sqlite3"
    job_repo = JobRepository(data_dir=data_dir, db_path=db_path)
    # If no event_bus is provided, create a dummy one for backward compatibility
    if event_bus is None:
        event_bus = EventBus()
    return JobService(job_repository=job_repo, event_bus=event_bus)


async def sync_games_job(data_dir: Path, event_bus: EventBus | None = None) -> None:
    db_path = data_dir / "main.sqlite3"

    job_service = _create_job_service(data_dir, event_bus)
    settings_repo = SettingsRepository(data_dir=data_dir, db_path=db_path)

    # Get configured usernames
    usernames = settings_repo.get_configured_usernames()

    if not usernames:
        logger.info("No usernames configured for sync")
        return

    # Sync each configured source
    for source, username in usernames.items():
        job_id = job_service.create_job(
            job_type="sync",
            username=username,
            source=source,
        )

        try:
            await _sync_single_source(data_dir, job_id, source, username, event_bus)
        except Exception as e:
            logger.error(f"Sync job {job_id} failed: {e}")
            job_service.update_job_status(job_id, "failed", str(e))

    # Update last sync timestamp
    settings_repo.set_setting("last_sync_timestamp", datetime.utcnow().isoformat())


async def _sync_single_source(
    data_dir: Path,
    job_id: str,
    source: str,
    username: str,
    event_bus: EventBus | None = None,
) -> None:
    from blunder_tutor.fetchers.chesscom import fetch as fetch_chesscom
    from blunder_tutor.fetchers.lichess import fetch as fetch_lichess
    from blunder_tutor.repositories.game_repository import GameRepository
    from blunder_tutor.repositories.settings import SettingsRepository

    db_path = data_dir / "main.sqlite3"

    job_service = _create_job_service(data_dir, event_bus)
    settings_repo = SettingsRepository(data_dir=data_dir, db_path=db_path)
    game_repo = GameRepository(data_dir=data_dir, db_path=db_path)

    job_service.update_job_status(job_id, "running")

    # Get max games setting
    max_games_str = settings_repo.get_setting("sync_max_games")
    max_games = int(max_games_str) if max_games_str else 1000

    # Initialize progress
    job_service.update_job_progress(job_id, 0, max_games)

    # Define progress callback
    def update_progress(current: int, total: int) -> None:
        job_service.update_job_progress(job_id, current, total)

    # Fetch games (runs in executor to avoid blocking)
    loop = asyncio.get_event_loop()

    try:
        if source == "lichess":
            # Use functools.partial to pass keyword argument to executor
            from functools import partial

            fetch_func = partial(
                fetch_lichess,
                username,
                data_dir,
                max_games,
                progress_callback=update_progress,
            )
            stored, skipped = await loop.run_in_executor(None, fetch_func)
        elif source == "chesscom":
            from functools import partial

            fetch_func = partial(
                fetch_chesscom,
                username,
                data_dir,
                max_games,
                progress_callback=update_progress,
            )
            stored, skipped = await loop.run_in_executor(None, fetch_func)
        else:
            raise ValueError(f"Unknown source: {source}")

        # Update final progress
        total_processed = stored + skipped
        job_service.update_job_progress(job_id, total_processed, total_processed)

        # Refresh game index cache
        await loop.run_in_executor(None, game_repo.refresh_index_cache)

        # Complete sync job BEFORE starting auto-analyze
        job_service.complete_job(job_id, {"stored": stored, "skipped": skipped})

        # Check if auto-analyze is enabled
        auto_analyze = settings_repo.get_setting("analyze_new_games_automatically")
        if auto_analyze == "true" and stored > 0:
            # Trigger analysis job for new games
            analyze_job_id = job_service.create_job(
                job_type="analyze",
                username=username,
                source=source,
                max_games=stored,
            )
            asyncio.create_task(
                _analyze_new_games(
                    data_dir, analyze_job_id, source, username, event_bus
                )
            )

    except Exception as e:
        logger.error(f"Error in sync job {job_id}: {e}")
        job_service.update_job_status(job_id, "failed", str(e))
        raise


async def _analyze_new_games(
    data_dir: Path,
    job_id: str,
    source: str,
    username: str,
    event_bus: EventBus | None = None,
) -> None:
    from blunder_tutor.analysis.logic import GameAnalyzer
    from blunder_tutor.index import read_index
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository

    main_db_path = data_dir / "main.sqlite3"
    job_service = _create_job_service(data_dir, event_bus)
    game_repo = GameRepository(data_dir=data_dir, db_path=main_db_path)
    analysis_repo = AnalysisRepository(data_dir=data_dir, db_path=main_db_path)

    job_service.update_job_status(job_id, "running")

    # Get unanalyzed games
    unanalyzed_games = []

    for record in read_index(data_dir, source=source, username=username):
        game_id = str(record.get("id"))
        if not analysis_repo.analysis_exists(game_id):
            unanalyzed_games.append(game_id)

    if not unanalyzed_games:
        job_service.complete_job(job_id, {"analyzed": 0, "skipped": 0})
        return

    job_service.update_job_progress(job_id, 0, len(unanalyzed_games))

    # Find engine path and create analyzer
    engine_path = _find_engine_path()
    analyzer = GameAnalyzer(
        analysis_repo=analysis_repo,
        games_repo=game_repo,
        engine_path=engine_path,
    )

    analyzed = 0
    loop = asyncio.get_event_loop()

    try:
        for i, game_id in enumerate(unanalyzed_games):
            # Run analysis in executor
            await loop.run_in_executor(
                None,
                analyzer.analyze_game,
                game_id,
                14,  # depth
                None,  # time_limit
                None,  # thresholds (use defaults)
            )

            # Mark game as analyzed in cache
            await loop.run_in_executor(None, game_repo.mark_game_analyzed, game_id)

            analyzed += 1
            job_service.update_job_progress(job_id, i + 1, len(unanalyzed_games))

        job_service.complete_job(job_id, {"analyzed": analyzed, "skipped": 0})

    except Exception as e:
        logger.error(f"Error in analysis job {job_id}: {e}")
        job_service.update_job_status(job_id, "failed", str(e))
        raise


async def analyze_games_job(
    data_dir: Path,
    job_id: str,
    game_ids: list[str],
    event_bus: EventBus | None = None,
) -> None:
    from blunder_tutor.analysis.logic import GameAnalyzer
    from blunder_tutor.repositories.analysis import AnalysisRepository
    from blunder_tutor.repositories.game_repository import GameRepository

    main_db_path = data_dir / "main.sqlite3"
    job_service = _create_job_service(data_dir, event_bus)
    game_repo = GameRepository(data_dir=data_dir, db_path=main_db_path)
    analysis_repo = AnalysisRepository(data_dir=data_dir, db_path=main_db_path)

    job_service.update_job_status(job_id, "running")
    job_service.update_job_progress(job_id, 0, len(game_ids))

    engine_path = _find_engine_path()
    analyzer = GameAnalyzer(
        analysis_repo=analysis_repo,
        games_repo=game_repo,
        engine_path=engine_path,
    )

    analyzed = 0
    skipped = 0
    loop = asyncio.get_event_loop()

    try:
        for i, game_id in enumerate(game_ids):
            # Skip if already analyzed
            if analysis_repo.analysis_exists(game_id):
                skipped += 1
                job_service.update_job_progress(job_id, i + 1, len(game_ids))
                continue

            # Run analysis in executor
            await loop.run_in_executor(None, analyzer.analyze_game, game_id)

            # Mark game as analyzed in cache
            await loop.run_in_executor(None, game_repo.mark_game_analyzed, game_id)

            analyzed += 1
            job_service.update_job_progress(job_id, i + 1, len(game_ids))

        job_service.complete_job(job_id, {"analyzed": analyzed, "skipped": skipped})

    except Exception as e:
        logger.error(f"Error in analysis job {job_id}: {e}")
        job_service.update_job_status(job_id, "failed", str(e))
        raise


def _find_engine_path() -> str:
    # Check environment variable
    env_path = os.environ.get("STOCKFISH_BINARY")
    if env_path and Path(env_path).exists():
        return env_path

    # Try common locations
    for path in [
        "/usr/games/stockfish",
        "/usr/local/bin/stockfish",
        "/usr/bin/stockfish",
        "stockfish",
    ]:
        if Path(path).exists():
            return path

    # Try in PATH
    import shutil

    which_path = shutil.which("stockfish")
    if which_path:
        return which_path

    raise FileNotFoundError("Stockfish engine not found")
