from collections.abc import Mapping, Sequence
from typing import TypeVar

from stash.config.model import ConfigError

_Choice = TypeVar("_Choice", bound=str)


class Section:
    def __init__(self, path: str, data: Mapping[str, object]) -> None:
        self._path = path
        self._remaining = dict(data)

    def take_optional_text(self, key: str) -> str | None:
        value = self._pop(key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise self._wrong_type(key, "a string")
        return value

    def take_text(self, key: str, default: str) -> str:
        value = self.take_optional_text(key)
        return default if value is None else value

    def take_required_text(self, key: str) -> str:
        value = self.take_optional_text(key)
        if value is None:
            raise ConfigError(f"{self._path_of(key)} is required")
        return value

    def take_integer(self, key: str, default: int) -> int:
        value = self._pop(key)
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            raise self._wrong_type(key, "an integer")
        return value

    def take_number(self, key: str, default: float) -> float:
        value = self._pop(key)
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise self._wrong_type(key, "a number")
        return float(value)

    def take_table(self, key: str) -> "Section | None":
        value = self._pop(key)
        if value is None:
            return None
        if not isinstance(value, dict):
            raise self._wrong_type(key, "a table")
        return Section(self._path_of(key), value)

    def take_table_or_empty(self, key: str) -> "Section":
        found = self.take_table(key)
        return Section(self._path_of(key), {}) if found is None else found

    def take_optional_choice(self, key: str, choices: Sequence[_Choice]) -> _Choice | None:
        value = self.take_optional_text(key)
        if value is None:
            return None
        for choice in choices:
            if choice == value:
                return choice
        raise ConfigError(f"{self._path_of(key)} must be one of {', '.join(choices)}")

    def take_choice(self, key: str, choices: Sequence[_Choice], default: _Choice) -> _Choice:
        value = self.take_optional_choice(key, choices)
        return default if value is None else value

    def take_required_choice(self, key: str, choices: Sequence[_Choice]) -> _Choice:
        value = self.take_optional_choice(key, choices)
        if value is None:
            raise ConfigError(f"{self._path_of(key)} is required (one of {', '.join(choices)})")
        return value

    def forbid(self, key: str, reason: str) -> None:
        if key in self._remaining:
            raise ConfigError(f"{self._path_of(key)} is not allowed: {reason}")

    def finish(self) -> None:
        if self._remaining:
            unknown = ", ".join(self._path_of(key) for key in sorted(self._remaining))
            raise ConfigError(f"unknown config key(s): {unknown}")

    def _pop(self, key: str) -> object | None:
        return self._remaining.pop(key, None)

    def _path_of(self, key: str) -> str:
        return f"{self._path}.{key}" if self._path else key

    def _wrong_type(self, key: str, expected: str) -> ConfigError:
        return ConfigError(f"{self._path_of(key)} must be {expected}")
