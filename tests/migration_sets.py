from importlib.resources import files
from pathlib import Path


def write_migrations(directory: Path, scripts: dict[str, str]) -> Path:
    directory.mkdir()
    for name, script in scripts.items():
        (directory / name).write_text(script, encoding="utf-8")
    return directory


def packaged_init_script() -> str:
    return (files("stash.store") / "migrations" / "0001_init.sql").read_text(encoding="utf-8")
