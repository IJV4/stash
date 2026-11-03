import argparse
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from stash import __version__
from stash.domain import ItemType, Stage, enum_member
from stash.evaluation import EvalArm
from stash.store.port import DEFAULT_PAGE_SIZE

DEFAULT_CASES = Path("evals/cases.jsonl")
MAX_LIMIT = 1000

_E = TypeVar("_E", bound=StrEnum)


class Command(StrEnum):
    DOCTOR = "doctor"
    LIST = "list"
    RETRY = "retry"
    GPU = "gpu"
    EVAL = "eval"
    BACKUP = "backup"


class GpuAction(StrEnum):
    STATUS = "status"
    OFF = "off"
    ON = "on"


def _choice(kind: type[_E]) -> Callable[[str], _E]:
    def convert(text: str) -> _E:
        member = enum_member(kind, text)
        if member is None:
            raise argparse.ArgumentTypeError(
                f"invalid choice {text!r} (choose from {', '.join(kind)})"
            )
        return member

    return convert


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    if value > MAX_LIMIT:
        raise argparse.ArgumentTypeError(f"invalid limit {value} (choose 1 to {MAX_LIMIT})")
    return value


def _names(text: str) -> tuple[str, ...]:
    names = tuple(name.strip() for name in text.split(","))
    if not all(names):
        raise argparse.ArgumentTypeError("names must be separated by single commas")
    return names


def _arms(text: str) -> tuple[EvalArm, ...]:
    valid = [arm.value for arm in EvalArm]
    names = _names(text)
    unknown = [name for name in names if name not in valid]
    if unknown:
        raise argparse.ArgumentTypeError(
            f"unknown arm {unknown[0]} (choose from {', '.join(valid)})"
        )
    return tuple(EvalArm(name) for name in names)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stash")
    parser.add_argument("--version", action="version", version=f"stash {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--config", metavar="PATH", help="config file (default: $STASH_CONFIG)")
    commands.add_parser(Command.DOCTOR, parents=[shared], help="check the setup")
    _add_list(commands, shared)
    commands.add_parser(Command.RETRY, parents=[shared], help="file every pending capture")
    gpu = commands.add_parser(Command.GPU, parents=[shared], help="show or switch the GPU gate")
    gpu.add_argument("action", type=_choice(GpuAction), choices=list(GpuAction))
    _add_eval(commands, shared)
    backup = commands.add_parser(Command.BACKUP, parents=[shared], help="back up the database")
    backup.add_argument("--to", required=True, type=Path, metavar="DIR")
    return parser


def _add_list(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]", shared: argparse.ArgumentParser
) -> None:
    listing = commands.add_parser(Command.LIST, parents=[shared], help="list saved items")
    listing.add_argument("--stage", type=_choice(Stage), choices=list(Stage))
    listing.add_argument("--type", dest="item_type", type=_choice(ItemType), choices=list(ItemType))
    listing.add_argument("--limit", type=_positive_int, default=DEFAULT_PAGE_SIZE)


def _add_eval(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]", shared: argparse.ArgumentParser
) -> None:
    evaluation = commands.add_parser(
        Command.EVAL, parents=[shared], help="compare models on the cases"
    )
    evaluation.add_argument("--providers", type=_names)
    evaluation.add_argument("--arms", type=_arms, default=tuple(EvalArm))
    evaluation.add_argument("--cases", type=Path, default=DEFAULT_CASES, metavar="PATH")
    evaluation.add_argument("--out", type=Path, metavar="PATH")
