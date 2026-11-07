from collections.abc import Callable, Iterable
from datetime import date, datetime, tzinfo
from pathlib import Path
from typing import Protocol, TextIO

from stash.capture import CaptureIntake, Reply
from stash.cli.failure import FAILURE, CommandFailed
from stash.doctor import Doctor
from stash.domain import ItemType, Stage
from stash.gpu_switch import GpuSwitch
from stash.lifecycle import LibraryQuery, Lifecycle, UnknownItem
from stash.rendering import (
    NO_ITEMS,
    NOTHING_PENDING,
    SWITCHED_ON,
    gpu_status_line,
    history_lines,
    library_line,
    listing_line,
    result_line,
    switched_off_lines,
)
from stash.store import BackupError, BackupWriter, ItemStore

MESSAGE_SEPARATOR = "\n\n"


class TickDelivery(Protocol):
    def deliver(self, now: datetime, send: Callable[[Reply], None]) -> None: ...

    def preview(self, now: datetime) -> tuple[Reply, ...]: ...


def _emit(lines: Iterable[str], out: TextIO) -> None:
    for line in lines:
        print(line, file=out)


def run_doctor(doctor: Doctor, out: TextIO) -> int:
    report = doctor.run()
    print(report.render(), file=out)
    return report.exit_code


def list_items(
    store: ItemStore, stage: Stage | None, item_type: ItemType | None, limit: int, out: TextIO
) -> int:
    items = store.list_items(stage=stage, item_type=item_type, limit=limit)
    _emit([listing_line(item) for item in items] or [NO_ITEMS], out)
    return 0


def retry(pipeline: CaptureIntake, out: TextIO) -> int:
    _emit([result_line(result) for result in pipeline.retry_pending()] or [NOTHING_PENDING], out)
    return 0


def gpu_status(switch: GpuSwitch, now: datetime, timezone: tzinfo, out: TextIO) -> int:
    print(gpu_status_line(switch.status(now.astimezone(timezone))), file=out)
    return 0


def gpu_off(switch: GpuSwitch, now: datetime, timezone: tzinfo, out: TextIO) -> int:
    _emit(switched_off_lines(switch.turn_off(now), timezone), out)
    return 0


def gpu_on(switch: GpuSwitch, out: TextIO) -> int:
    switch.turn_on()
    print(SWITCHED_ON, file=out)
    return 0


def backup(backups: BackupWriter, today: date, directory: Path, out: TextIO) -> int:
    try:
        written = backups.write(directory, today)
    except BackupError as error:
        raise CommandFailed(f"cannot write a backup to {directory}: {error}", FAILURE) from error
    print(f"Backup written: {written}", file=out)
    return 0


def library(lifecycle: Lifecycle, query: LibraryQuery, out: TextIO) -> int:
    entries = lifecycle.library(query)
    lines = [
        f"{entry.item.id}  {library_line(entry.item, entry.last_outcome)}" for entry in entries
    ]
    _emit(lines or [NO_ITEMS], out)
    return 0


def show(lifecycle: Lifecycle, item_id: str, out: TextIO) -> int:
    try:
        history = lifecycle.history(item_id)
    except UnknownItem as error:
        raise CommandFailed(str(error), FAILURE) from error
    _emit(history_lines(history), out)
    return 0


def tick(delivery: TickDelivery, now: datetime, dry_run: bool, out: TextIO) -> int:
    if dry_run:
        replies = delivery.preview(now)
    else:
        sent: list[Reply] = []
        delivery.deliver(now, sent.append)
        replies = tuple(sent)
    if replies:
        print(MESSAGE_SEPARATOR.join(reply.text for reply in replies), file=out)
    return 0
