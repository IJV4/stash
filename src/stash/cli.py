import argparse
from collections.abc import Sequence

from stash import __version__


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="stash")
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    arguments = parser.parse_args(argv)
    if arguments.version:
        print(f"stash {__version__}")
    return 0
