import argparse

import uvicorn

from blunder_tutor.cli.base import CLICommand
from blunder_tutor.constants import DEFAULT_ENGINE_DEPTH
from blunder_tutor.web.app import AppConfig, create_app


class TrainUICommand(CLICommand):
    def should_run(self, args: argparse.Namespace) -> bool:
        return args.command == "train-ui"

    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        app = create_app(
            config,
        )
        uvicorn.run(app, host=args.host, port=args.port)

    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        train_ui_parser = subparsers.add_parser(
            "train-ui", help="Start local blunder training UI"
        )
        train_ui_parser.add_argument(
            "--source",
            choices=("lichess", "chesscom"),
            help="Filter by source",
        )
        train_ui_parser.add_argument(
            "--depth",
            type=int,
            default=DEFAULT_ENGINE_DEPTH,
            help="Engine analysis depth",
        )
        train_ui_parser.add_argument(
            "--time",
            type=float,
            default=None,
            help="Time limit per position (seconds)",
        )
        train_ui_parser.add_argument(
            "--host",
            default="0.0.0.0",
            help="Host to bind the server to",
        )
        train_ui_parser.add_argument(
            "--port",
            type=int,
            default=8000,
            help="Port to bind the server to",
        )
        return
