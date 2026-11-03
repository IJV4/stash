import datetime as dt
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from stash.domain import Filing, ItemType, Route, Stage


class EvalField(StrEnum):
    ROUTE = "route"
    ITEM_TYPE = "item_type"
    STAGE = "stage"
    DATE = "date"
    DETAILS = "details"


@dataclass(frozen=True, slots=True)
class FieldVerdict:
    passed: frozenset[EvalField]
    failed: frozenset[EvalField]

    def __post_init__(self) -> None:
        if self.passed & self.failed:
            raise ValueError("a field cannot be both passed and failed")

    @classmethod
    def all_failed(cls, fields: frozenset[EvalField]) -> "FieldVerdict":
        return cls(frozenset(), fields)


@dataclass(frozen=True, slots=True)
class Expectation:
    route: Route
    item_type: ItemType | None = None
    stage: Stage | None = None
    date: dt.date | None = None
    details: Mapping[str, str] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "details", MappingProxyType(dict(self.details)))

    def scored_fields(self) -> frozenset[EvalField]:
        return frozenset(self._checks())

    def judge(self, filing: Filing) -> FieldVerdict:
        outcomes = {field: check(filing) for field, check in self._checks().items()}
        return FieldVerdict(
            passed=frozenset(field for field, agrees in outcomes.items() if agrees),
            failed=frozenset(field for field, agrees in outcomes.items() if not agrees),
        )

    def _checks(self) -> dict[EvalField, Callable[[Filing], bool]]:
        checks: dict[EvalField, Callable[[Filing], bool]] = {
            EvalField.ROUTE: lambda filing: filing.route == self.route
        }
        if self.item_type is not None:
            checks[EvalField.ITEM_TYPE] = lambda filing: filing.item_type == self.item_type
        if self.stage is not None:
            checks[EvalField.STAGE] = lambda filing: filing.stage == self.stage
        if self.date is not None:
            checks[EvalField.DATE] = lambda filing: filing.date == self.date
        if self.details:
            checks[EvalField.DETAILS] = lambda filing: _contains_all(filing.details, self.details)
        return checks


def _contains_all(filed: Mapping[str, str], expected: Mapping[str, str]) -> bool:
    return all(
        key in filed and wanted.casefold() in filed[key].casefold()
        for key, wanted in expected.items()
    )
