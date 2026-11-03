from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Owners:
    _user_ids: frozenset[str]

    @classmethod
    def parse(cls, raw: str | None) -> Owners:
        entries = (entry.strip() for entry in (raw or "").split(","))
        return cls(frozenset(entry for entry in entries if entry))

    def admits_user(self, user_id: str) -> bool:
        return user_id in self._user_ids

    def admits_nobody(self) -> bool:
        return not self._user_ids
