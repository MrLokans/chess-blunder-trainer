import argparse
import asyncio

from tqdm import tqdm

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories import GameRepository
from blunder_tutor.repositories.analysis import AnalysisRepository
from blunder_tutor.services.eco_backfill_service import ECOBackfillService
from blunder_tutor.web.config import AppConfig


class BackfillECOCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "backfill-eco"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        db_path = config.data.db_path
        run_migrations(db_path)

        analysis_repo = AnalysisRepository.from_config(config)
        games_repo = GameRepository.from_config(config)

        try:
            backfill_service = ECOBackfillService(
                analysis_repo=analysis_repo,
                game_repo=games_repo,
            )

            game_ids = await backfill_service.get_games_needing_backfill()

            if not game_ids:
                print("No games need ECO backfill.")
                return

            print(f"Found {len(game_ids)} games needing ECO classification.")

            classified = 0
            with tqdm(
                total=len(game_ids), desc="Backfilling ECO codes", unit="game"
            ) as pbar:
                for game_id in game_ids:
                    was_classified = await backfill_service.backfill_game(game_id)
                    if was_classified:
                        classified += 1
                    pbar.update(1)

            print(
                f"Backfill complete: {len(game_ids)} games processed, "
                f"{classified} games classified with ECO codes."
            )

        finally:
            await analysis_repo.close()
            await games_repo.close()

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        subparsers.add_parser(
            "backfill-eco",
            help="Backfill ECO opening codes for analyzed games missing ECO info",
        )
