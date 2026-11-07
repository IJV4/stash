from importlib.resources import files
from pathlib import Path

INIT_SCRIPT = "0001_init.sql"
LIFECYCLE_SCRIPT = "0002_lifecycle.sql"
STEPS_SCRIPT = "0003_steps_nudges.sql"
PEOPLE_SCRIPT = "0004_people.sql"


def write_migrations(directory: Path, scripts: dict[str, str]) -> Path:
    directory.mkdir()
    for name, script in scripts.items():
        (directory / name).write_text(script, encoding="utf-8")
    return directory


def packaged_scripts(*names: str) -> dict[str, str]:
    packaged = files("stash.store") / "migrations"
    return {name: (packaged / name).read_text(encoding="utf-8") for name in names}


def packaged_init_script() -> str:
    return packaged_scripts(INIT_SCRIPT)[INIT_SCRIPT]
