from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from stash.config import LIBRARY_TOKEN_VAR
from stash.config.library import MIN_TOKEN_LENGTH, TOKEN_ALPHABET

LIBRARY_COPY_DIRECTORY = "library"
LIBRARY_COPY_NAME = "latest.html"
TOKEN_GENERATOR = 'python3 -c "import secrets; print(secrets.token_urlsafe(32))"'
TOKEN_MISSING_MESSAGE = (
    f"set {LIBRARY_TOKEN_VAR} to {MIN_TOKEN_LENGTH} or more characters of {TOKEN_ALPHABET}; "
    f"generate one with {TOKEN_GENERATOR}"
)


class ServingLibrary(Protocol):
    def serve_forever(self) -> None: ...

    def shutdown(self) -> None: ...


LibraryServerFactory = Callable[[Callable[[], str], str, str, int], ServingLibrary]


class LibraryTokenMissing(Exception):
    def __init__(self) -> None:
        super().__init__(TOKEN_MISSING_MESSAGE)


def library_copy_path(data_dir: Path) -> Path:
    return data_dir / LIBRARY_COPY_DIRECTORY / LIBRARY_COPY_NAME
