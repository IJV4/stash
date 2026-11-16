import errno
import logging
import os
import stat
from collections.abc import Sequence
from pathlib import Path

from stash.app.atomic_write import write_atomically

logger = logging.getLogger(__name__)

MEDIA_DIRECTORY = "media"
MAX_MEDIA_BYTES = 20 * 1024 * 1024
ALLOWED_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".ogg", ".oga", ".mp3", ".m4a", ".wav"}
)
FALLBACK_SUFFIX = ".bin"
DIRECTORY_MODE = 0o700
FILE_MODE = 0o600
MISSING = "the file is missing"
NOT_REGULAR = "not a regular file (a symlink or another kind of file)"
TOO_LARGE = "the file is over the size limit"
UNREADABLE = "the file cannot be read"
NOT_WRITABLE = "the copy could not be written"
READ_CHUNK_BYTES = 1024 * 1024


class _Skipped(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class DirectoryMediaKeeper:
    def __init__(self, root: Path, max_bytes: int = MAX_MEDIA_BYTES) -> None:
        self._root = root
        self._max_bytes = max_bytes

    def keep(self, capture_id: str, paths: Sequence[str]) -> tuple[str, ...]:
        return tuple(self._kept(capture_id, number, path) for number, path in enumerate(paths))

    def discard(self, paths: Sequence[str]) -> None:
        for path in paths:
            target = Path(path)
            if target.parent != self._root:
                continue
            try:
                target.unlink(missing_ok=True)
            except OSError as error:
                logger.warning(
                    "media copy not removed: %s", errno.errorcode.get(error.errno or 0, "OSError")
                )

    def _kept(self, capture_id: str, number: int, path: str) -> str:
        try:
            data = self._read(path)
            target = self._root / f"{capture_id}-{number}{_suffix_of(path)}"
            try:
                self._root.mkdir(mode=DIRECTORY_MODE, parents=True, exist_ok=True)
                write_atomically(target, data)
                target.chmod(FILE_MODE)
            except OSError:
                raise _Skipped(NOT_WRITABLE) from None
        except _Skipped as skipped:
            logger.warning(
                "capture %s: media %d not copied: %s", capture_id, number, skipped.reason
            )
            return path
        except OSError as error:
            logger.warning(
                "capture %s: media %d not copied: %s (%s)",
                capture_id,
                number,
                UNREADABLE,
                errno.errorcode.get(error.errno or 0, "OSError"),
            )
            return path
        return str(target)

    def _read(self, path: str) -> bytes:
        try:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            raise _Skipped(MISSING) from None
        except OSError as error:
            if error.errno == errno.ELOOP:
                raise _Skipped(NOT_REGULAR) from None
            raise
        try:
            status = os.fstat(descriptor)
            if not stat.S_ISREG(status.st_mode):
                raise _Skipped(NOT_REGULAR)
            if status.st_size > self._max_bytes:
                raise _Skipped(TOO_LARGE)
            data = _read_up_to(descriptor, self._max_bytes + 1)
        finally:
            os.close(descriptor)
        if len(data) > self._max_bytes:
            raise _Skipped(TOO_LARGE)
        return data


def _read_up_to(descriptor: int, limit: int) -> bytes:
    chunks: list[bytes] = []
    remaining = limit
    while remaining > 0:
        chunk = os.read(descriptor, min(remaining, READ_CHUNK_BYTES))
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _suffix_of(path: str) -> str:
    suffix = Path(path).suffix.lower()
    return suffix if suffix in ALLOWED_SUFFIXES else FALLBACK_SUFFIX
