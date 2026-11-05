import datetime as dt
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from stash.domain import Filing, ItemType, Route, Stage, printable_and_clip

MISSING = "none"
MISMATCH_TEXT_LIMIT = 80

Scalar = Route | ItemType | Stage | dt.date


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
class FieldMismatch:
    field: EvalField
    expected: str
    got: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "expected", printable_and_clip(self.expected, MISMATCH_TEXT_LIMIT))
        object.__setattr__(self, "got", printable_and_clip(self.got, MISMATCH_TEXT_LIMIT))


@dataclass(frozen=True, slots=True)
class Assessment:
    verdict: FieldVerdict
    mismatches: tuple[FieldMismatch, ...]


@dataclass(frozen=True, slots=True)
class _Check:
    agrees: bool
    expected: str
    got: str


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
        return frozenset(self._scored())

    def judge(self, filing: Filing) -> FieldVerdict:
        return self.assess(filing).verdict

    def mismatches(self, filing: Filing) -> tuple[FieldMismatch, ...]:
        return self.assess(filing).mismatches

    def assess(self, filing: Filing) -> Assessment:
        checks = self._checked(filing)
        verdict = FieldVerdict(
            passed=frozenset(field for field, check in checks.items() if check.agrees),
            failed=frozenset(field for field, check in checks.items() if not check.agrees),
        )
        mismatches = tuple(
            FieldMismatch(field, check.expected, check.got)
            for field, check in checks.items()
            if not check.agrees
        )
        return Assessment(verdict, mismatches)

    def _checked(self, filing: Filing) -> dict[EvalField, _Check]:
        return {field: check(filing) for field, check in self._scored().items()}

    def _scored(self) -> dict[EvalField, Callable[[Filing], _Check]]:
        scored: dict[EvalField, Callable[[Filing], _Check]] = {
            EvalField.ROUTE: lambda filing: _equal(self.route, filing.route)
        }
        if self.item_type is not None:
            scored[EvalField.ITEM_TYPE] = lambda filing: _equal(self.item_type, filing.item_type)
        if self.stage is not None:
            scored[EvalField.STAGE] = lambda filing: _equal(self.stage, filing.stage)
        if self.date is not None:
            scored[EvalField.DATE] = lambda filing: _equal(self.date, filing.date)
        if self.details:
            scored[EvalField.DETAILS] = lambda filing: _details_check(self.details, filing.details)
        return scored


def _equal(expected: Scalar | None, got: Scalar | None) -> _Check:
    return _Check(expected == got, _text(expected), _text(got))


def _text(value: Scalar | None) -> str:
    if value is None:
        return MISSING
    if isinstance(value, StrEnum):
        return value.value
    return value.isoformat()


def _details_check(expected: Mapping[str, str], filed: Mapping[str, str]) -> _Check:
    return _Check(
        _contains_all(filed, expected),
        _pairs(expected, expected),
        _pairs(expected, filed),
    )


def _pairs(keys: Mapping[str, str], values: Mapping[str, str]) -> str:
    return ", ".join(f"{key}={values.get(key, MISSING)}" for key in keys)


def _contains_all(filed: Mapping[str, str], expected: Mapping[str, str]) -> bool:
    return all(
        key in filed and wanted.casefold() in filed[key].casefold()
        for key, wanted in expected.items()
    )
