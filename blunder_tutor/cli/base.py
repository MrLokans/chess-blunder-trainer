import abc
import argparse

from blunder_tutor.web.config import AppConfig


class CLICommand(abc.ABC):
    @abc.abstractmethod
    def should_run(self, args: argparse.Namespace) -> bool:
        pass

    @abc.abstractmethod
    def run(self, args: argparse.Namespace, config: AppConfig) -> None:
        pass

    @abc.abstractmethod
    def register_subparser(self, subparsers: argparse._SubParsersAction) -> None:
        pass
