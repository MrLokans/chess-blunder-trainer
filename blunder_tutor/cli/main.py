import argparse
import os
from pathlib import Path

from blunder_tutor import constants
from blunder_tutor.cli.analyze import AnalyzeCommand
from blunder_tutor.cli.analyze_bulk import AnalyzeBulkCommand
from blunder_tutor.cli.fetch import FetchCommand
from blunder_tutor.cli.index import IndexCommand
from blunder_tutor.cli.list import ListCommand
from blunder_tutor.cli.train_ui import TrainUICommand
from blunder_tutor.web.config import config_factory

COMMANDS = [
    FetchCommand(),
    ListCommand(),
    IndexCommand(),
    AnalyzeCommand(),
    AnalyzeBulkCommand(),
    TrainUICommand(),
]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="blunder-tutor")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=constants.DEFAULT_DATA_PATH,
        help="Local storage directory",
    )
    parser.add_argument(
        "--engine-path",
        type=str,
        default=None,
        help="Full path to the stockfish binary",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in COMMANDS:
        command.register_subparser(subparsers=subparsers)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    application_config = config_factory(args, os.environ)

    for command in COMMANDS:
        if command.should_run(args):
            return command.run(args, application_config)

    parser.print_help()
