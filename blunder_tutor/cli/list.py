import argparse
import asyncio

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.web.config import AppConfig


class ListCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "list"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        asyncio.run(self._run_async(args, config))

    async def _run_async(self, args: argparse.Namespace, config: AppConfig) -> None:
        repo = GameRepository.from_config(config=config)
        count = 0
        async for record in repo.list_games(
            source=args.source, username=args.username, limit=args.limit
        ):
            print(
                f"{record.get('id')} | {record.get('source')} | "
                f"{record.get('white')} vs {record.get('black')} | "
                f"{record.get('result')} | {record.get('date')}"
            )
            count += 1
        print(f"Listed {count} games.")
        await repo.close()

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        list_parser = subparsers.add_parser("list", help="List stored games")
        list_parser.add_argument(
            "--source",
            choices=("lichess", "chesscom"),
            help="Filter by source",
        )
        list_parser.add_argument("--username", help="Filter by username")
        list_parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Max results to show",
        )
        return
