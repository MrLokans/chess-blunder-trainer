#!/usr/bin/env python3
"""
Profile the full analysis pipeline using pre-downloaded benchmark games.

Runs the pipeline across a matrix of concurrency settings, collects hardware
info, phase timings, cProfile data, and writes everything into a timestamped
directory under ./profiling/.

Prerequisites:
    uv run python scripts/download_benchmark_games.py   # one-time

Usage:
    # Default: benchmark depth=9,11 × pool_size=2,4,6,8 × sf_threads=1,2 on 40 games
    uv run python scripts/profile_bulk_analysis.py

    # Custom matrix
    uv run python scripts/profile_bulk_analysis.py --depths 9,11,15 --pool-sizes 2,4 --sf-threads 1,2 --limit 20

    # Visualize previous results
    uv run python scripts/profile_bulk_analysis.py visualize
    uv run python scripts/profile_bulk_analysis.py visualize --run-dir profiling/2026-02-09T12-00-00
"""

from __future__ import annotations

import argparse
import asyncio
import cProfile
import json
import logging
import os
import platform
import pstats
import subprocess
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from blunder_tutor.analysis.engine_pool import WorkCoordinator
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.constants import DEFAULT_ENGINE_DEPTH
from blunder_tutor.fetchers.filesystem import load_from_directory
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.web.config import get_engine_path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)-20s] %(levelname)-5s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("profiler")

BENCHMARK_DIR = Path("fixtures/benchmark/drnykterstein")
PROFILING_ROOT = Path("profiling")


# ---------------------------------------------------------------------------
# Hardware / environment info
# ---------------------------------------------------------------------------


def _git_commit_short() -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return "unknown"


def _git_dirty() -> bool:
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet"], capture_output=True, timeout=5
        )
        return result.returncode != 0
    except Exception:
        return False


def _stockfish_version(engine_path: str) -> str:
    try:
        proc = subprocess.run(
            [engine_path],
            input="uci\nquit\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in proc.stdout.splitlines():
            if line.startswith("id name"):
                return line.removeprefix("id name").strip()
    except Exception:
        pass
    return "unknown"


def collect_environment(engine_path: str, depths: list[int]) -> dict:
    uname = platform.uname()
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "platform": {
            "system": uname.system,
            "release": uname.release,
            "machine": uname.machine,
            "processor": platform.processor(),
            "cpu_count": os.cpu_count(),
            "python_version": platform.python_version(),
        },
        "git": {
            "commit": _git_commit_short(),
            "dirty": _git_dirty(),
        },
        "engine": {
            "path": engine_path,
            "version": _stockfish_version(engine_path),
            "depths": depths,
        },
    }


# ---------------------------------------------------------------------------
# Timing infrastructure
# ---------------------------------------------------------------------------


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

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[int(len(s) * p / 100)]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_s": round(self.total, 4),
            "count": self.count,
            "avg_s": round(self.avg, 4),
            "p50_s": round(self.percentile(50), 4),
            "p95_s": round(self.percentile(95), 4),
            "p99_s": round(self.percentile(99), 4),
        }


class Profiler:
    def __init__(self) -> None:
        self.buckets: dict[str, TimingBucket] = {}
        self._wall_start: float = 0.0
        self._wall_end: float = 0.0

    @contextmanager
    def measure(self, name: str):
        start = time.perf_counter()
        yield
        b = self.buckets.setdefault(name, TimingBucket(name))
        b.record(time.perf_counter() - start)

    def measure_value(self, name: str, elapsed: float) -> None:
        b = self.buckets.setdefault(name, TimingBucket(name))
        b.record(elapsed)

    def wall_start(self) -> None:
        self._wall_start = time.perf_counter()

    def wall_stop(self) -> None:
        self._wall_end = time.perf_counter()

    @property
    def wall_time(self) -> float:
        return self._wall_end - self._wall_start

    def to_dict(self) -> dict:
        return {
            "wall_time_s": round(self.wall_time, 4),
            "buckets": {
                name: b.to_dict()
                for name, b in sorted(
                    self.buckets.items(), key=lambda kv: kv[1].total, reverse=True
                )
            },
        }

    def format_report(self) -> str:
        lines = [
            "",
            "=" * 90,
            f"  Wall time: {self.wall_time:.2f}s",
            "",
            f"  {'Bucket':<30} {'Count':>6} {'Total':>8} {'Avg':>8} {'P50':>8} {'P95':>8} {'P99':>8}",
            "  " + "-" * 84,
        ]
        for b in sorted(self.buckets.values(), key=lambda x: x.total, reverse=True):
            lines.append(
                f"  {b.name:<30} {b.count:>6} {b.total:>7.2f}s {b.avg:>7.3f}s "
                f"{b.percentile(50):>7.3f}s {b.percentile(95):>7.3f}s {b.percentile(99):>7.3f}s"
            )
        lines.append("=" * 90)
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Single-run benchmark
# ---------------------------------------------------------------------------


async def _run_single_benchmark(
    game_records: list[dict[str, object]],
    db_path: Path,
    engine_path: str,
    depth: int,
    pool_size: int,
    threads_per_engine: int | None,
) -> tuple[Profiler, dict, cProfile.Profile]:
    run_migrations(db_path)

    game_repo = GameRepository(db_path)
    analysis_repo = AnalysisRepository(db_path)
    profiler = Profiler()

    try:
        await game_repo.insert_games(game_records)
        game_ids = [g["id"] for g in game_records]

        analyzer = GameAnalyzer(
            analysis_repo=analysis_repo,
            games_repo=game_repo,
            engine_path=engine_path,
        )

        coordinator = WorkCoordinator(
            engine_path,
            pool_size,
            threads_per_engine=threads_per_engine,
        )
        await coordinator.start()

        lock = asyncio.Lock()
        results = {"analyzed": 0, "skipped": 0, "failed": 0}

        cp = cProfile.Profile()
        cp.enable()
        profiler.wall_start()

        try:
            for game_id in game_ids:

                async def process_game(
                    engine,
                    *,
                    _gid: str = game_id,
                ) -> None:
                    with profiler.measure("game.total"):
                        try:
                            report = await analyzer.analyze_game(
                                _gid, depth=depth, engine=engine
                            )
                            for step_id, dur in report.step_durations.items():
                                profiler.measure_value(f"step.{step_id}", dur)
                            await game_repo.mark_game_analyzed(_gid)
                            async with lock:
                                results["analyzed"] += 1
                        except Exception as e:
                            logger.error("Failed %s: %s", _gid, e)
                            async with lock:
                                results["failed"] += 1

                coordinator.submit(process_game)

            await coordinator.drain()
        finally:
            await coordinator.shutdown()

        profiler.wall_stop()
        cp.disable()

        return profiler, results, cp

    finally:
        await analysis_repo.close()
        await game_repo.close()
        if db_path.exists():
            db_path.unlink()


# ---------------------------------------------------------------------------
# Main benchmark command
# ---------------------------------------------------------------------------


async def cmd_benchmark(args: argparse.Namespace) -> None:
    if not BENCHMARK_DIR.exists():
        print(
            f"Benchmark data not found at {BENCHMARK_DIR}.\n"
            "Run: uv run python scripts/download_benchmark_games.py"
        )
        sys.exit(1)

    engine_path = get_engine_path(os.environ)
    depths = [int(x) for x in args.depths.split(",")]
    limit = args.limit
    pool_sizes = [int(x) for x in args.pool_sizes.split(",")]
    sf_threads_list = [int(x) for x in args.sf_threads.split(",")]

    game_records = load_from_directory(BENCHMARK_DIR, max_games=limit)
    n_games = len(game_records)
    logger.info("Loaded %d benchmark games from %s", n_games, BENCHMARK_DIR)

    env_info = collect_environment(engine_path, depths)
    env_info["benchmark"] = {
        "n_games": n_games,
        "pool_sizes": pool_sizes,
        "sf_threads": sf_threads_list,
        "depths": depths,
    }

    ts = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = PROFILING_ROOT / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "environment.json").write_text(
        json.dumps(env_info, indent=2), encoding="utf-8"
    )
    logger.info("Results will be saved to %s", run_dir)

    all_run_results = []
    pipeline_steps = ["eco", "stockfish", "move_quality", "phase", "traps", "write"]

    matrix = [
        (ps, thr, d) for d in depths for ps in pool_sizes for thr in sf_threads_list
    ]
    total_combos = len(matrix)

    for idx, (pool_size, sf_threads, depth) in enumerate(matrix, 1):
        label = f"pool={pool_size}, sf_threads={sf_threads}, depth={depth}"
        logger.info("--- [%d/%d] Benchmarking %s ---", idx, total_combos, label)

        file_tag = f"pool{pool_size}_thr{sf_threads}_d{depth}"
        tmp_db = run_dir / f"_tmp_{file_tag}.sqlite3"
        profiler, results, cp = await _run_single_benchmark(
            game_records=game_records,
            db_path=tmp_db,
            engine_path=engine_path,
            depth=depth,
            pool_size=pool_size,
            threads_per_engine=sf_threads,
        )

        throughput = (
            results["analyzed"] / profiler.wall_time if profiler.wall_time else 0
        )

        run_result = {
            "pool_size": pool_size,
            "sf_threads": sf_threads,
            "depth": depth,
            "n_games": n_games,
            "wall_time_s": round(profiler.wall_time, 4),
            "throughput_games_per_s": round(throughput, 4),
            "results": results,
            "pipeline_steps": pipeline_steps,
            "timings": profiler.to_dict(),
        }
        all_run_results.append(run_result)

        cp.dump_stats(str(run_dir / f"{file_tag}.prof"))

        s = StringIO()
        ps = pstats.Stats(cp, stream=s)
        ps.sort_stats("cumulative")
        ps.print_stats(50)
        (run_dir / f"{file_tag}_cprofile.txt").write_text(
            s.getvalue(), encoding="utf-8"
        )

        print(f"\n{'=' * 90}")
        print(
            f"  pool={pool_size}  sf_threads={sf_threads}  depth={depth}  |  "
            f"{n_games} games"
        )
        print(
            f"  Wall time: {profiler.wall_time:.2f}s  |  Throughput: {throughput:.2f} games/s"
        )
        print(f"  Results: {results}")
        print(profiler.format_report())

    summary = {
        "environment": env_info,
        "runs": all_run_results,
    }
    (run_dir / "results.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )

    _print_summary_table(all_run_results)
    logger.info("All results saved to %s", run_dir)
    logger.info(
        "Visualize with: uv run python scripts/profile_bulk_analysis.py visualize --run-dir %s",
        run_dir,
    )


def _print_summary_table(runs: list[dict]) -> None:
    print("\n" + "=" * 90)
    print("  SUMMARY")
    print("=" * 90)
    print(
        f"  {'Depth':>6} {'Pool':>6} {'SF Thr':>8} {'Games':>7} {'Wall (s)':>10} "
        f"{'Games/s':>10} {'Analyzed':>10} {'Failed':>8}"
    )
    print("  " + "-" * 82)
    for r in runs:
        print(
            f"  {r['depth']:>6} {r['pool_size']:>6} {r['sf_threads']:>8} "
            f"{r['n_games']:>7} {r['wall_time_s']:>10.2f} "
            f"{r['throughput_games_per_s']:>10.2f} "
            f"{r['results']['analyzed']:>10} {r['results']['failed']:>8}"
        )
    print("=" * 90)


# ---------------------------------------------------------------------------
# Visualize command
# ---------------------------------------------------------------------------


def cmd_visualize(args: argparse.Namespace) -> None:
    if args.run_dir:
        run_dirs = [Path(args.run_dir)]
    else:
        if not PROFILING_ROOT.exists():
            print("No profiling data found. Run a benchmark first.")
            sys.exit(1)
        run_dirs = sorted(
            [d for d in PROFILING_ROOT.iterdir() if d.is_dir()],
            key=lambda d: d.name,
        )
        if not run_dirs:
            print("No profiling runs found.")
            sys.exit(1)

    all_runs: list[dict] = []
    for rd in run_dirs:
        results_path = rd / "results.json"
        if not results_path.exists():
            continue
        data = json.loads(results_path.read_text(encoding="utf-8"))
        env = data.get("environment", {})
        commit = env.get("git", {}).get("commit", "?")
        engine_ver = env.get("engine", {}).get("version", "?")
        ts = env.get("timestamp", rd.name)

        for run in data.get("runs", []):
            sf_thr = run.get("sf_threads") or run.get("threads_per_engine") or "auto"
            all_runs.append(
                {
                    "run_dir": rd.name,
                    "timestamp": ts,
                    "commit": commit,
                    "engine": engine_ver,
                    "pool_size": run["pool_size"],
                    "sf_threads": sf_thr,
                    "depth": run.get("depth", "?"),
                    "n_games": run["n_games"],
                    "wall_time_s": run["wall_time_s"],
                    "throughput": run["throughput_games_per_s"],
                    "analyzed": run["results"]["analyzed"],
                    "failed": run["results"]["failed"],
                }
            )

    if not all_runs:
        print("No run data found.")
        sys.exit(1)

    _render_text_chart(all_runs)

    if len(run_dirs) > 1:
        _render_comparison_table(all_runs)


def _render_text_chart(runs: list[dict]) -> None:
    max_throughput = max(r["throughput"] for r in runs)
    bar_width = 50

    print("\n" + "=" * 80)
    print("  THROUGHPUT (games/s)")
    print("=" * 80)

    current_run_dir = None
    for r in runs:
        if r["run_dir"] != current_run_dir:
            current_run_dir = r["run_dir"]
            print(f"\n  [{r['run_dir']}]  commit={r['commit']}  engine={r['engine']}")

        bar_len = (
            int(r["throughput"] / max_throughput * bar_width) if max_throughput else 0
        )
        bar = "█" * bar_len
        label = f"d={str(r['depth']):<3} pool={r['pool_size']:<2} thr={str(r['sf_threads']):<4}"
        print(
            f"    {label} │{bar} {r['throughput']:.2f} g/s  ({r['wall_time_s']:.1f}s)"
        )

    print()


def _render_comparison_table(runs: list[dict]) -> None:
    combos = sorted({(r["depth"], r["pool_size"], r["sf_threads"]) for r in runs})

    col_width = 14
    header_cols = "".join(
        f" {'d' + str(d) + '/p' + str(p) + '/t' + str(t):>{col_width}}"
        for d, p, t in combos
    )

    print("=" * 80)
    print("  COMPARISON ACROSS RUNS  (columns: depth/pool/threads)")
    print("=" * 80)
    print(f"  {'Run':<24} {'Commit':<10}{header_cols}")
    print("  " + "-" * (24 + 10 + len(combos) * (col_width + 1)))

    by_run: dict[str, dict[tuple, float]] = {}
    run_meta: dict[str, dict] = {}
    for r in runs:
        key = (r["depth"], r["pool_size"], r["sf_threads"])
        by_run.setdefault(r["run_dir"], {})[key] = r["throughput"]
        run_meta[r["run_dir"]] = r

    for run_dir, throughputs in by_run.items():
        meta = run_meta[run_dir]
        row = f"  {run_dir:<24} {meta['commit']:<10}"
        for combo in combos:
            val = throughputs.get(combo)
            row += f" {val:>{col_width - 1}.2f}g" if val else f" {'—':>{col_width}}"
        print(row)

    print("=" * 80)
    print("  (values are games/s — d=depth, p=pool_size, t=sf_threads)")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Profile the analysis pipeline with benchmark games",
    )
    sub = parser.add_subparsers(dest="command")

    bench_p = sub.add_parser("benchmark", help="Run benchmark (default)")
    bench_p.add_argument(
        "--limit", type=int, default=40, help="Max games to process (default: 40)"
    )
    bench_p.add_argument(
        "--depths",
        default=f"9,{DEFAULT_ENGINE_DEPTH}",
        help=f"Comma-separated engine depths to sweep (default: 9,{DEFAULT_ENGINE_DEPTH})",
    )
    bench_p.add_argument(
        "--pool-sizes",
        default="2,4,6,8",
        help="Comma-separated pool sizes to benchmark (default: 2,4,6,8)",
    )
    bench_p.add_argument(
        "--sf-threads",
        default="1,2",
        help="Comma-separated Stockfish threads per engine to sweep (default: 1,2)",
    )

    viz_p = sub.add_parser("visualize", help="Visualize profiling results")
    viz_p.add_argument(
        "--run-dir",
        default=None,
        help="Specific run directory to visualize (default: all)",
    )

    args = parser.parse_args()
    command = args.command or "benchmark"

    if command == "visualize":
        cmd_visualize(args)
    else:
        # Re-parse with benchmark defaults when no subcommand given
        if args.command is None:
            args = bench_p.parse_args([])
        asyncio.run(cmd_benchmark(args))


if __name__ == "__main__":
    main()
