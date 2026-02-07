#!/usr/bin/env python3
"""
Profile bulk analysis to find performance bottlenecks.

Usage:
    # Step 1: Fetch games into a temporary DB
    uv run python scripts/profile_bulk_analysis.py fetch --username DrNykterstein --max 200

    # Step 2: Profile the bulk analysis
    uv run python scripts/profile_bulk_analysis.py analyze --limit 50 --concurrency 4

    # Full pipeline (fetch + analyze)
    uv run python scripts/profile_bulk_analysis.py run --username DrNykterstein --max 200 --limit 50

    # Clean up
    uv run python scripts/profile_bulk_analysis.py clean

Environment:
    STOCKFISH_BINARY    Path to stockfish (auto-detected if not set)
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import logging
import pstats
import shutil
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.constants import DEFAULT_ENGINE_DEPTH
from blunder_tutor.fetchers import lichess
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.web.config import get_engine_path

import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("profiler")

PROFILE_DATA_DIR = Path("data/profile")
PROFILE_DB_PATH = PROFILE_DATA_DIR / "profile.sqlite3"
PROFILE_OUTPUT_DIR = PROFILE_DATA_DIR / "results"


@dataclass
class TimingBucket:
    name: str
    total: float = 0.0
    count: int = 0
    samples: list[float] = field(default_factory=list)

    def record(self, elapsed: float) -> None:
        self.total += elapsed
        self.count += 1
        self.samples.append(elapsed)

    @property
    def avg(self) -> float:
        return self.total / self.count if self.count else 0.0

    @property
    def p50(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[len(s) // 2]

    @property
    def p95(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[int(len(s) * 0.95)]

    @property
    def p99(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[int(len(s) * 0.99)]


class AnalysisProfiler:
    def __init__(self) -> None:
        self.buckets: dict[str, TimingBucket] = {}
        self._wall_start: float = 0.0
        self._wall_end: float = 0.0

    def bucket(self, name: str) -> TimingBucket:
        if name not in self.buckets:
            self.buckets[name] = TimingBucket(name)
        return self.buckets[name]

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        yield
        self.bucket(name).record(time.perf_counter() - start)

    def wall_start(self) -> None:
        self._wall_start = time.perf_counter()

    def wall_stop(self) -> None:
        self._wall_end = time.perf_counter()

    @property
    def wall_time(self) -> float:
        return self._wall_end - self._wall_start

    def report(self) -> str:
        lines = []
        lines.append("")
        lines.append("=" * 80)
        lines.append("PROFILING RESULTS")
        lines.append("=" * 80)
        lines.append(f"Wall time: {self.wall_time:.2f}s")
        lines.append("")
        lines.append(
            f"{'Bucket':<30} {'Count':>6} {'Total':>8} {'Avg':>8} "
            f"{'P50':>8} {'P95':>8} {'P99':>8}"
        )
        lines.append("-" * 80)

        for b in sorted(self.buckets.values(), key=lambda x: x.total, reverse=True):
            lines.append(
                f"{b.name:<30} {b.count:>6} {b.total:>7.2f}s {b.avg:>7.3f}s "
                f"{b.p50:>7.3f}s {b.p95:>7.3f}s {b.p99:>7.3f}s"
            )

        lines.append("=" * 80)
        return "\n".join(lines)


def _get_engine_path() -> str:
    return get_engine_path(os.environ)


async def cmd_fetch(args: argparse.Namespace) -> None:
    PROFILE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    run_migrations(PROFILE_DB_PATH)

    game_repo = GameRepository(PROFILE_DB_PATH)
    try:
        username = args.username
        max_games = args.max

        logger.info(
            "Fetching up to %d games for %s from Lichess...", max_games, username
        )
        t0 = time.perf_counter()
        games, _seen = await lichess.fetch(
            username=username,
            max_games=max_games,
        )
        fetch_time = time.perf_counter() - t0
        logger.info("Fetched %d games in %.1fs", len(games), fetch_time)

        inserted = await game_repo.insert_games(games)
        logger.info(
            "Inserted %d new games (skipped %d)", inserted, len(games) - inserted
        )
    finally:
        await game_repo.close()


async def cmd_analyze(args: argparse.Namespace) -> None:
    run_migrations(PROFILE_DB_PATH)
    engine_path = _get_engine_path()
    concurrency = args.concurrency
    depth = args.depth
    limit = args.limit

    analysis_repo = AnalysisRepository(PROFILE_DB_PATH)
    game_repo = GameRepository(PROFILE_DB_PATH)

    try:
        game_ids = await game_repo.list_unanalyzed_game_ids()
        if limit:
            game_ids = game_ids[:limit]

        if not game_ids:
            logger.warning("No unanalyzed games found. Run 'fetch' first.")
            return

        logger.info(
            "Profiling analysis: %d games, depth=%d, concurrency=%d",
            len(game_ids),
            depth,
            concurrency,
        )

        profiler = AnalysisProfiler()

        # Monkey-patch key methods to collect timings
        _orig_load_game = game_repo.load_game
        _orig_analysis_exists = analysis_repo.analysis_exists
        _orig_write_analysis = analysis_repo.write_analysis
        _orig_mark_steps = analysis_repo.mark_steps_completed
        _orig_mark_analyzed = game_repo.mark_game_analyzed
        _orig_is_step_completed = analysis_repo.is_step_completed

        async def timed_load_game(gid):
            with profiler.measure("db.load_game"):
                return await _orig_load_game(gid)

        async def timed_analysis_exists(gid):
            with profiler.measure("db.analysis_exists"):
                return await _orig_analysis_exists(gid)

        async def timed_write_analysis(**kw):
            with profiler.measure("db.write_analysis"):
                return await _orig_write_analysis(**kw)

        async def timed_mark_steps(gid, steps):
            with profiler.measure("db.mark_steps_completed"):
                return await _orig_mark_steps(gid, steps)

        async def timed_mark_analyzed(gid):
            with profiler.measure("db.mark_game_analyzed"):
                return await _orig_mark_analyzed(gid)

        async def timed_is_step_completed(gid, sid):
            with profiler.measure("db.is_step_completed"):
                return await _orig_is_step_completed(gid, sid)

        game_repo.load_game = timed_load_game
        analysis_repo.analysis_exists = timed_analysis_exists
        analysis_repo.write_analysis = timed_write_analysis
        analysis_repo.mark_steps_completed = timed_mark_steps
        analysis_repo.mark_game_analyzed = timed_mark_analyzed
        analysis_repo.is_step_completed = timed_is_step_completed

        # Patch engine.analyse to time Stockfish calls
        import chess.engine

        _orig_analyse = chess.engine.UciProtocol.analyse

        async def timed_analyse(self, board, limit, **kw):
            with profiler.measure("engine.analyse"):
                return await _orig_analyse(self, board, limit, **kw)

        chess.engine.UciProtocol.analyse = timed_analyse

        # Run analysis
        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=engine_path,
        )

        coordinator = WorkCoordinator(engine_path, concurrency)
        await coordinator.start()

        lock = asyncio.Lock()
        results = {"analyzed": 0, "skipped": 0, "failed": 0}
        processed = 0

        profiler.wall_start()
        cprofile = cProfile.Profile()
        cprofile.enable()

        try:
            for game_id in game_ids:

                async def process_game(
                    engine: chess.engine.UciProtocol,
                    *,
                    _gid: str = game_id,
                ) -> None:
                    nonlocal processed
                    with profiler.measure("game.total"):
                        try:
                            await analyzer.analyze_game(
                                _gid,
                                depth=depth,
                                engine=engine,
                            )
                            await game_repo.mark_game_analyzed(_gid)
                            async with lock:
                                results["analyzed"] += 1
                                processed += 1
                        except Exception as e:
                            logger.error("Failed %s: %s", _gid, e)
                            async with lock:
                                results["failed"] += 1
                                processed += 1

                    if processed % 10 == 0:
                        logger.info(
                            "Progress: %d/%d (%.0f%%)",
                            processed,
                            len(game_ids),
                            100 * processed / len(game_ids),
                        )

                coordinator.submit(process_game)

            await coordinator.drain()
        finally:
            await coordinator.shutdown()

        cprofile.disable()
        profiler.wall_stop()

        # Restore patches
        chess.engine.UciProtocol.analyse = _orig_analyse

        # Print timing report
        print(profiler.report())

        throughput = (
            results["analyzed"] / profiler.wall_time if profiler.wall_time else 0
        )
        print(f"\nThroughput: {throughput:.2f} games/sec")
        print(f"Results: {results}")

        engine_total = profiler.buckets.get("engine.analyse")
        db_total = sum(
            b.total for name, b in profiler.buckets.items() if name.startswith("db.")
        )
        game_total = profiler.buckets.get("game.total")
        if game_total and engine_total:
            engine_pct = engine_total.total / (game_total.total or 1) * 100
            db_pct = db_total / (game_total.total or 1) * 100
            other_pct = 100 - engine_pct - db_pct
            print(f"\nTime breakdown (sum of per-game wall time):")
            print(f"  Engine:  {engine_total.total:>8.1f}s ({engine_pct:.1f}%)")
            print(f"  DB:      {db_total:>8.1f}s ({db_pct:.1f}%)")
            print(
                f"  Other:   {game_total.total - engine_total.total - db_total:>8.1f}s ({other_pct:.1f}%)"
            )

        # Save cProfile output
        PROFILE_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        pstats_path = PROFILE_OUTPUT_DIR / "bulk_analysis.prof"
        cprofile.dump_stats(str(pstats_path))
        logger.info("cProfile data saved to %s", pstats_path)
        logger.info("  View with: python -m pstats %s", pstats_path)
        logger.info("  Or:        uv run snakeviz %s", pstats_path)

        # Also dump top 30 cumulative
        print("\n" + "=" * 80)
        print("TOP 30 FUNCTIONS BY CUMULATIVE TIME (cProfile)")
        print("=" * 80)
        s = StringIO()
        ps = pstats.Stats(cprofile, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(30)
        print(s.getvalue())

    finally:
        await analysis_repo.close()
        await game_repo.close()


async def cmd_run(args: argparse.Namespace) -> None:
    await cmd_fetch(args)
    await cmd_analyze(args)


def cmd_clean(_args: argparse.Namespace) -> None:
    if PROFILE_DATA_DIR.exists():
        shutil.rmtree(PROFILE_DATA_DIR)
        logger.info("Removed %s", PROFILE_DATA_DIR)
    else:
        logger.info("Nothing to clean")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile bulk analysis performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    fetch_p = sub.add_parser("fetch", help="Fetch games into profile DB")
    fetch_p.add_argument("--username", default="DrNykterstein")
    fetch_p.add_argument("--max", type=int, default=200)

    analyze_p = sub.add_parser("analyze", help="Profile bulk analysis")
    analyze_p.add_argument("--limit", type=int, default=None)
    analyze_p.add_argument("--depth", type=int, default=DEFAULT_ENGINE_DEPTH)
    analyze_p.add_argument("--concurrency", "-j", type=int, default=4)

    run_p = sub.add_parser("run", help="Fetch + analyze in one go")
    run_p.add_argument("--username", default="DrNykterstein")
    run_p.add_argument("--max", type=int, default=200)
    run_p.add_argument("--limit", type=int, default=None)
    run_p.add_argument("--depth", type=int, default=DEFAULT_ENGINE_DEPTH)
    run_p.add_argument("--concurrency", "-j", type=int, default=4)

    sub.add_parser("clean", help="Remove profile data")

    args = parser.parse_args()

    if args.command == "clean":
        cmd_clean(args)
    elif args.command == "fetch":
        asyncio.run(cmd_fetch(args))
    elif args.command == "analyze":
        asyncio.run(cmd_analyze(args))
    elif args.command == "run":
        asyncio.run(cmd_run(args))


if __name__ == "__main__":
    main()
