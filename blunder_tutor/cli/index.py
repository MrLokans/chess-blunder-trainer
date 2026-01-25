import argparse

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.index import rebuild_index
from blunder_tutor.web.config import AppConfig


class IndexCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "index"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        count = rebuild_index(
            data_dir=args.data_dir,
            source=args.source,
            username=args.username,
            reset=args.reset,
        )
        print(f"Indexed {count} games.")

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        index_parser = subparsers.add_parser("index", help="Backfill metadata index")
        index_parser.add_argument(
            "--source",
            choices=("lichess", "chesscom"),
            help="Filter by source",
        )
        index_parser.add_argument("--username", help="Filter by username")
        index_parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset index before rebuilding",
        )
        return
