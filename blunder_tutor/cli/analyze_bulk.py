import argparse
import asyncio

from blunder_tutor.analysis.logic import DEFAULT_CONCURRENCY, GameAnalyzer
from blunder_tutor.cli.base import CLICommand
from blunder_tutor.constants import DEFAULT_ENGINE_DEPTH
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories import GameRepository
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.web.config import AppConfig


class AnalyzeBulkCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "analyze-bulk"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        db_path = config.data.db_path
        run_migrations(db_path)

        analysis_repo = AnalysisRepository.from_config(config)
        games_repo = GameRepository.from_config(config)
        try:
            analyzer = GameAnalyzer(
                analysis_repo=analysis_repo,
                games_repo=games_repo,
                engine_path=config.engine_path,
            )
            result = await analyzer.analyze_bulk(
                depth=args.depth,
                time_limit=args.time,
                source=args.source,
                username=args.username,
                limit=args.limit,
                force=args.force,
                concurrency=args.concurrency,
            )
            print(
                "Bulk analysis complete: "
                f"processed {result['processed']}, "
                f"analyzed {result['analyzed']}, "
                f"skipped {result['skipped']}."
            )
        finally:
            await analysis_repo.close()
            await games_repo.close()

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        analyze_bulk_parser = subparsers.add_parser(
            "analyze-bulk", help="Analyze multiple stored games"
        )
        analyze_bulk_parser.add_argument(
            "--source",
            choices=("lichess", "chesscom"),
            help="Filter by source",
        )
        analyze_bulk_parser.add_argument("--username", help="Filter by username")
        analyze_bulk_parser.add_argument(
            "--depth",
            type=int,
            default=DEFAULT_ENGINE_DEPTH,
            help="Engine analysis depth",
        )
        analyze_bulk_parser.add_argument(
            "--time",
            type=float,
            default=None,
            help="Time limit per position (seconds)",
        )
        analyze_bulk_parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Max games to analyze",
        )
        analyze_bulk_parser.add_argument(
            "--force",
            action="store_true",
            help="Re-analyze already analyzed games",
        )
        analyze_bulk_parser.add_argument(
            "--concurrency",
            "-j",
            type=int,
            default=DEFAULT_CONCURRENCY,
            help=f"Number of parallel engine processes (default: {DEFAULT_CONCURRENCY})",
        )
        return
