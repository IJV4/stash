import argparse
from typing import TextIO, assert_never

from stash.app import StashApp, write_atomically
from stash.cli import commands
from stash.cli.eval_command import EvalRequest, run_eval_command
from stash.cli.parser import Command, GpuAction
from stash.lifecycle import LibraryQuery


def dispatch(arguments: argparse.Namespace, app: StashApp, out: TextIO) -> int:
    command = Command(arguments.command)
    match command:
        case Command.DOCTOR:
            return commands.run_doctor(app.doctor, out)
        case Command.LIST:
            return commands.list_items(
                app.store, arguments.stage, arguments.item_type, arguments.limit, out
            )
        case Command.RETRY:
            return commands.retry(app.pipeline, out)
        case Command.GPU:
            return _gpu(arguments.action, app, out)
        case Command.EVAL:
            request = EvalRequest(
                providers=arguments.providers,
                thinking=arguments.thinking,
                arms=arguments.arms,
                cases=arguments.cases,
                out=arguments.out,
            )
            return run_eval_command(
                request, app.eval_targets, app.ocr, app.clock, app.config.timezone, out
            )
        case Command.BACKUP:
            return commands.backup(app.backups, app.today(), arguments.to, out)
        case Command.LIBRARY:
            return _library(arguments, app, out)
        case Command.SHOW:
            return commands.show(app.lifecycle, arguments.item_id, out)
        case Command.TICK:
            return commands.tick(app.nudge_delivery, app.clock(), arguments.dry_run, out)
        case Command.PEOPLE:
            return commands.people(app.people, app.today(), arguments.upcoming, out)
        case Command.SERVE:
            return commands.serve(app.library_server, app.config.library, out)
        case _:
            assert_never(command)


def _library(arguments: argparse.Namespace, app: StashApp, out: TextIO) -> int:
    if arguments.html is not None:
        return commands.library_html(app.rendered_library, write_atomically, arguments.html, out)
    query = LibraryQuery(arguments.item_type, arguments.limit)
    return commands.library(app.lifecycle, query, out)


def _gpu(action: GpuAction, app: StashApp, out: TextIO) -> int:
    timezone = app.config.timezone
    match action:
        case GpuAction.STATUS:
            return commands.gpu_status(app.gpu_switch, app.local_now(), timezone, out)
        case GpuAction.OFF:
            return commands.gpu_off(app.gpu_switch, app.local_now(), timezone, out)
        case GpuAction.ON:
            return commands.gpu_on(app.gpu_switch, out)
        case _:
            assert_never(action)
