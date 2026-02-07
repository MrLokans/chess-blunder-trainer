import argparse
import asyncio

from blunder_tutor.analysis.logic import GameAnalyzer
from blunder_tutor.analysis.pipeline import PipelinePreset
from blunder_tutor.cli.base import CLICommand
from blunder_tutor.constants import DEFAULT_ENGINE_DEPTH
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories import GameRepository
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.web.config import AppConfig

AVAILABLE_STEPS = ["eco", "stockfish", "move_quality", "phase", "write"]


class AnalyzeCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "analyze"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        run_migrations(config.data.db_path)

        analysis_repo = AnalysisRepository.from_config(config)
        games_repo = GameRepository.from_config(config)
        try:
            analyzer = GameAnalyzer(
                analysis_repo=analysis_repo,
                games_repo=games_repo,
                engine_path=config.engine_path,
            )

            steps = args.steps if args.steps else None

            await analyzer.analyze_game(
                game_id=args.game_id,
                depth=args.depth,
                time_limit=args.time,
                steps=steps,
                force_rerun=args.force,
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
            default=DEFAULT_ENGINE_DEPTH,
            help="Engine analysis depth",
        )
        analyze_parser.add_argument(
            "--time",
            type=float,
            default=None,
            help="Time limit per position (seconds)",
        )
        analyze_parser.add_argument(
            "--steps",
            nargs="+",
            choices=AVAILABLE_STEPS,
            default=None,
            help=f"Pipeline steps to run. Available: {', '.join(AVAILABLE_STEPS)}. "
            f"Default: full pipeline ({', '.join(PipelinePreset.FULL.value)})",
        )
        analyze_parser.add_argument(
            "--force",
            action="store_true",
            help="Force re-run steps even if already completed",
        )
        return
