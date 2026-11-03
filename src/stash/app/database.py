import sqlite3
from contextlib import ExitStack

from stash.config import ConfigError, StashConfig
from stash.store.sqlite import SqliteStore


def open_database(config: StashConfig, resources: ExitStack) -> SqliteStore:
    path = config.db_path
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        store = SqliteStore(path)
    except (OSError, sqlite3.Error) as error:
        raise ConfigError(f"cannot open the database at {path}: {error}") from error
    resources.callback(store.close)
    return store
