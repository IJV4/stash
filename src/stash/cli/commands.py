from datetime import date, datetime, tzinfo
from pathlib import Path
from typing import TextIO

from stash.capture import CaptureIntake
from stash.cli.failure import FAILURE, CommandFailed
from stash.doctor import Doctor
from stash.domain import ItemType, Stage
from stash.gpu_switch import GpuSwitch
from stash.rendering import (
    NO_ITEMS,
    NOTHING_PENDING,
    SWITCHED_ON,
    gpu_status_line,
    listing_line,
    result_line,
    switched_off_lines,
)
from stash.store import BackupError, BackupWriter, ItemStore


def run_doctor(doctor: Doctor, out: TextIO) -> int:
    report = doctor.run()
    print(report.render(), file=out)
    return report.exit_code


def list_items(
    store: ItemStore, stage: Stage | None, item_type: ItemType | None, limit: int, out: TextIO
) -> int:
    items = store.list_items(stage=stage, item_type=item_type, limit=limit)
    for line in [listing_line(item) for item in items] or [NO_ITEMS]:
        print(line, file=out)
    return 0


def retry(pipeline: CaptureIntake, out: TextIO) -> int:
    for line in [result_line(result) for result in pipeline.retry_pending()] or [NOTHING_PENDING]:
        print(line, file=out)
    return 0


def gpu_status(switch: GpuSwitch, now: datetime, timezone: tzinfo, out: TextIO) -> int:
    print(gpu_status_line(switch.status(now.astimezone(timezone))), file=out)
    return 0


def gpu_off(switch: GpuSwitch, now: datetime, timezone: tzinfo, out: TextIO) -> int:
    for line in switched_off_lines(switch.turn_off(now), timezone):
        print(line, file=out)
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
