from pathlib import Path

LIBRARY_COPY_DIRECTORY = "library"
LIBRARY_COPY_NAME = "latest.html"


def library_copy_path(data_dir: Path) -> Path:
    return data_dir / LIBRARY_COPY_DIRECTORY / LIBRARY_COPY_NAME
