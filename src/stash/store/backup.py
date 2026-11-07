import logging
import os
import re
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol, Self

from stash.store.port import BACKUP_LAST_SUCCESS_KEY, BackupError, BackupSource

logger = logging.getLogger(__name__)

DEFAULT_KEEP = 30
_BACKUP_NAME = re.compile(r"stash-([0-9]{4})([0-9]{2})([0-9]{2})\.db")
_TEMPORARY_PREFIX = ".stash-backup-"
RECORD_FAILED_LOG = "could not record the backup time: %s"


@dataclass(frozen=True, slots=True, order=True)
class BackupName:
    day: date

    @classmethod
    def for_day(cls, day: date) -> Self:
        return cls(day)

    @classmethod
    def parse(cls, filename: str) -> Self | None:
        match = _BACKUP_NAME.fullmatch(filename)
        if match is None:
            return None
        year, month, day = (int(group) for group in match.groups())
        try:
            return cls(date(year, month, day))
        except ValueError:
            return None

    def __str__(self) -> str:
        return f"stash-{self.day.year:04d}{self.day.month:02d}{self.day.day:02d}.db"


class BackupSettings(Protocol):
    def put_setting(self, key: str, value: str) -> None: ...


class Backups:
    def __init__(
        self,
        source: BackupSource,
        settings: BackupSettings,
        clock: Callable[[], datetime],
        keep: int = DEFAULT_KEEP,
        remove: Callable[[Path], None] = Path.unlink,
    ) -> None:
        if keep < 1:
            raise ValueError("keep must be at least 1")
        self._source = source
        self._settings = settings
        self._clock = clock
        self._keep = keep
        self._remove = remove

    def write(self, directory: Path, today: date) -> Path:
        backup = directory / str(BackupName.for_day(today))
        try:
            directory.mkdir(parents=True, exist_ok=True)
            self._copy_into_place(directory, backup)
        except OSError as error:
            raise BackupError(f"cannot write to {directory}: {error}") from error
        self._record_success_best_effort()
        self._prune_best_effort(directory)
        return backup

    def _copy_into_place(self, directory: Path, backup: Path) -> None:
        descriptor, temporary_name = tempfile.mkstemp(prefix=_TEMPORARY_PREFIX, dir=directory)
        os.close(descriptor)
        temporary = Path(temporary_name)
        try:
            self._source.backup_to(temporary)
            os.replace(temporary, backup)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise

    def _record_success_best_effort(self) -> None:
        try:
            self._settings.put_setting(BACKUP_LAST_SUCCESS_KEY, self._clock().isoformat())
        except Exception as error:
            logger.warning(RECORD_FAILED_LOG, type(error).__name__)

    def _prune_best_effort(self, directory: Path) -> None:
        try:
            self._prune(directory)
        except OSError as error:
            logger.warning("could not prune old backups: %s", type(error).__name__)

    def _prune(self, directory: Path) -> None:
        backups = sorted(
            (
                (name, path)
                for path in directory.iterdir()
                if path.is_file() and (name := BackupName.parse(path.name)) is not None
            ),
            reverse=True,
        )
        for _, path in backups[self._keep :]:
            self._remove(path)
