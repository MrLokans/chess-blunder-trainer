import argparse

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.repositories.game_repository import GameRepository
from blunder_tutor.web.config import AppConfig


class ShowCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "show"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        repo = GameRepository.from_config(config=config)
        record = repo.get_game(args.game_id)
        if record:
            print(record)
        else:
            print(f"Game not found: {args.game_id}")

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        show_parser = subparsers.add_parser("show", help="Show stored game metadata")
        show_parser.add_argument("game_id", help="Game id (sha256)")
        return
