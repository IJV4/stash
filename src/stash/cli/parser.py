import argparse
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from stash import __version__
from stash.config import Thinking
from stash.domain import MAX_ROSTER_WINDOW_DAYS, ItemType, Stage, enum_member
from stash.evaluation import EvalArm
from stash.lifecycle import MAX_LIBRARY_LIMIT, MIN_LIBRARY_LIMIT
from stash.store.port import DEFAULT_PAGE_SIZE

DEFAULT_CASES = Path("evals/cases.jsonl")
MIN_LIMIT = 1
MAX_LIMIT = 1000
MIN_UPCOMING_DAYS = 1

_E = TypeVar("_E", bound=StrEnum)


class Command(StrEnum):
    DOCTOR = "doctor"
    LIST = "list"
    RETRY = "retry"
    GPU = "gpu"
    EVAL = "eval"
    BACKUP = "backup"
    LIBRARY = "library"
    SHOW = "show"
    TICK = "tick"
    PEOPLE = "people"


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


def _limit_between(minimum: int, maximum: int) -> Callable[[str], int]:
    def convert(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{text!r} is not a number") from None
        if value < minimum:
            raise argparse.ArgumentTypeError(f"must be at least {minimum}")
        if value > maximum:
            raise argparse.ArgumentTypeError(
                f"invalid limit {value} (choose {minimum} to {maximum})"
            )
        return value

    return convert


def _names(text: str) -> tuple[str, ...]:
    names = tuple(name.strip() for name in text.split(","))
    if not all(names):
        raise argparse.ArgumentTypeError("names must be separated by single commas")
    return names


def _enum_list(kind: type[_E], noun: str) -> Callable[[str], tuple[_E, ...]]:
    valid = [member.value for member in kind]

    def convert(text: str) -> tuple[_E, ...]:
        names = _names(text)
        unknown = [name for name in names if name not in valid]
        if unknown:
            raise argparse.ArgumentTypeError(
                f"unknown {noun} {unknown[0]} (choose from {', '.join(valid)})"
            )
        return tuple(kind(name) for name in names)

    return convert


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
    _add_library(commands, shared)
    show = commands.add_parser(Command.SHOW, parents=[shared], help="show an item's history")
    show.add_argument("item_id")
    tick = commands.add_parser(Command.TICK, parents=[shared], help="send the nudges that are due")
    tick.add_argument("--dry-run", action="store_true", help="print them without marking them sent")
    _add_people(commands, shared)
    return parser


def _add_list(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]", shared: argparse.ArgumentParser
) -> None:
    listing = commands.add_parser(Command.LIST, parents=[shared], help="list saved items")
    listing.add_argument("--stage", type=_choice(Stage), choices=list(Stage))
    listing.add_argument("--type", dest="item_type", type=_choice(ItemType), choices=list(ItemType))
    listing.add_argument(
        "--limit", type=_limit_between(MIN_LIMIT, MAX_LIMIT), default=DEFAULT_PAGE_SIZE
    )


def _add_library(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]", shared: argparse.ArgumentParser
) -> None:
    library = commands.add_parser(Command.LIBRARY, parents=[shared], help="list kept items")
    library.add_argument("--type", dest="item_type", type=_choice(ItemType), choices=list(ItemType))
    library.add_argument(
        "--limit",
        type=_limit_between(MIN_LIBRARY_LIMIT, MAX_LIBRARY_LIMIT),
        default=DEFAULT_PAGE_SIZE,
    )


def _add_people(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]", shared: argparse.ArgumentParser
) -> None:
    people = commands.add_parser(Command.PEOPLE, parents=[shared], help="list people and dates")
    people.add_argument(
        "--upcoming",
        type=_limit_between(MIN_UPCOMING_DAYS, MAX_ROSTER_WINDOW_DAYS),
        metavar="DAYS",
        help="only people whose next key date is within DAYS days",
    )


def _add_eval(
    commands: "argparse._SubParsersAction[argparse.ArgumentParser]", shared: argparse.ArgumentParser
) -> None:
    evaluation = commands.add_parser(
        Command.EVAL, parents=[shared], help="compare models on the cases"
    )
    evaluation.add_argument("--providers", type=_names)
    evaluation.add_argument("--thinking", type=_enum_list(Thinking, "thinking"))
    evaluation.add_argument("--arms", type=_enum_list(EvalArm, "arm"), default=tuple(EvalArm))
    evaluation.add_argument("--cases", type=Path, default=DEFAULT_CASES, metavar="PATH")
    evaluation.add_argument("--out", type=Path, metavar="PATH")
