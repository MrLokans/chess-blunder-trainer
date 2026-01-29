import argparse
import asyncio

from blunder_tutor.analysis.db import ensure_schema
from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.cli.base import CLICommand
from blunder_tutor.repositories import GameRepository
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.web.config import AppConfig


class AnalyzeCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "analyze"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        ensure_schema(config.data.db_path)

        analysis_repo = AnalysisRepository.from_config(config)
        games_repo = GameRepository.from_config(config)
        try:
            analyzer = GameAnalyzer(
                analysis_repo=analysis_repo,
                games_repo=games_repo,
                engine_path=config.engine_path,
            )

            await analyzer.analyze_game(
                game_id=args.game_id,
                depth=args.depth,
                time_limit=args.time,
            )
            print(f"Analysis complete for game {args.game_id}")
        finally:
            await analysis_repo.close()
            await games_repo.close()

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        analyze_parser = subparsers.add_parser("analyze", help="Analyze a stored game")
        analyze_parser.add_argument("game_id", help="Game id (sha256)")
        analyze_parser.add_argument(
            "--depth",
            type=int,
            default=14,
            help="Engine analysis depth",
        )
        analyze_parser.add_argument(
            "--time",
            type=float,
            default=None,
            help="Time limit per position (seconds)",
        )
        return
