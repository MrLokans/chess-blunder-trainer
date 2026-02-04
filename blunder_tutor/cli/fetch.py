import argparse
import asyncio
from datetime import datetime

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.fetchers import chesscom, lichess
from blunder_tutor.migrations import run_migrations
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.web.config import AppConfig


class FetchCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "fetch"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        run_migrations(config.data.db_path)
        game_repo = GameRepository.from_config(config)

        try:
            since = await self._resolve_since(args, game_repo)
            if since:
                print(f"Incremental fetch: only games after {since.isoformat()}")

            if args.source == "lichess":
                games, _seen_ids = await lichess.fetch(
                    username=args.username,
                    max_games=args.max,
                    since=since,
                    batch_size=args.batch_size,
                )
                inserted = await game_repo.insert_games(games)
                skipped = len(games) - inserted
                print(f"Lichess: stored {inserted}, skipped {skipped}.")
                return

            if args.source == "chesscom":
                games, _seen_ids = await chesscom.fetch(
                    username=args.username,
                    max_games=args.max,
                    since=since,
                )
                inserted = await game_repo.insert_games(games)
                skipped = len(games) - inserted
                print(f"Chess.com: stored {inserted}, skipped {skipped}.")
                return
        finally:
            await game_repo.close()

    async def _resolve_since(
        self, args: argparse.Namespace, game_repo: GameRepository
    ) -> datetime | None:
        if getattr(args, "incremental", False):
            return await game_repo.get_latest_game_time(args.source, args.username)
        if getattr(args, "since", None):
            return datetime.fromisoformat(args.since)
        return None

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        fetch_parser = subparsers.add_parser("fetch", help="Fetch games by username")
        fetch_subparsers = fetch_parser.add_subparsers(dest="source", required=True)

        lichess_parser = fetch_subparsers.add_parser(
            "lichess", help="Fetch from Lichess"
        )
        lichess_parser.add_argument("username", help="Lichess username")
        lichess_parser.add_argument(
            "--max",
            type=int,
            default=None,
            help="Max number of games to fetch",
        )
        lichess_parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Lichess pagination batch size",
        )
        lichess_parser.add_argument(
            "--incremental",
            action="store_true",
            help="Only fetch games newer than the latest in database",
        )
        lichess_parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Only fetch games after this ISO datetime (e.g., 2024-01-15T00:00:00)",
        )

        chesscom_parser = fetch_subparsers.add_parser(
            "chesscom", help="Fetch from Chess.com"
        )
        chesscom_parser.add_argument("username", help="Chess.com username")
        chesscom_parser.add_argument(
            "--max",
            type=int,
            default=None,
            help="Max number of games to fetch",
        )
        chesscom_parser.add_argument(
            "--incremental",
            action="store_true",
            help="Only fetch games newer than the latest in database",
        )
        chesscom_parser.add_argument(
            "--since",
            type=str,
            default=None,
            help="Only fetch games after this ISO datetime (e.g., 2024-01-15T00:00:00)",
        )

        return
