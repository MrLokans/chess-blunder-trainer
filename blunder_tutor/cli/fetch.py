import argparse

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.fetchers import chesscom, lichess
from blunder_tutor.web.config import AppConfig


class FetchCommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "fetch"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        if args.command == "fetch" and args.source == "lichess":
            stored, skipped = lichess.fetch(
                username=args.username,
                data_dir=args.data_dir,
                max_games=args.max,
                batch_size=args.batch_size,
            )
            print(f"Lichess: stored {stored}, skipped {skipped}.")
            return

        if args.command == "fetch" and args.source == "chesscom":
            stored, skipped = chesscom.fetch(
                username=args.username,
                data_dir=args.data_dir,
                max_games=args.max,
            )
            print(f"Chess.com: stored {stored}, skipped {skipped}.")
            return

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

        return
