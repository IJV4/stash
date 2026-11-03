import os
import sys
from collections.abc import Callable, Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from typing import TextIO

from stash.app import StashApp, build_app
from stash.cli.config_path import config_path
from stash.cli.dispatch import dispatch
from stash.cli.failure import USAGE_ERROR, CommandFailed
from stash.cli.parser import build_parser
from stash.config import ConfigError, StashConfig
from stash.config.loader import load_config


def main(
    argv: Sequence[str] | None = None,
    *,
    factory: Callable[[StashConfig], StashApp] = build_app,
    env: Mapping[str, str] | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
) -> int:
    stdout = sys.stdout if out is None else out
    stderr = sys.stderr if err is None else err
    environment = os.environ if env is None else env
    with redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            arguments = build_parser().parse_args(argv)
        except SystemExit as stop:
            return stop.code if isinstance(stop.code, int) else USAGE_ERROR
    try:
        app = factory(load_config(config_path(arguments.config, environment), environment))
    except ConfigError as error:
        print(error, file=stderr)
        return USAGE_ERROR
    try:
        return dispatch(arguments, app, stdout)
    except CommandFailed as failure:
        print(failure, file=stderr)
        return failure.exit_code
    finally:
        app.close()
