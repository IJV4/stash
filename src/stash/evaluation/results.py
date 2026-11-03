import statistics
from dataclasses import dataclass
from enum import StrEnum

from stash.domain import require_text
from stash.evaluation.expectation import EvalField


class EvalArm(StrEnum):
    TEXT = "text"
    VISION = "vision"
    OCR = "ocr"


@dataclass(frozen=True, slots=True)
class CaseResult:
    case_id: str
    arm: EvalArm
    passed_fields: frozenset[EvalField]
    failed_fields: frozenset[EvalField]
    latency_s: float
    error: str | None

    def scored(self, field: EvalField) -> bool:
        return field in self.passed_fields or field in self.failed_fields

    def passed(self, field: EvalField) -> bool:
        return field in self.passed_fields


@dataclass(frozen=True, slots=True)
class EvalRun:
    label: str
    results: tuple[CaseResult, ...]

    def __post_init__(self) -> None:
        require_text("label", self.label)
        object.__setattr__(self, "results", tuple(self.results))

    def arms(self) -> tuple[EvalArm, ...]:
        return tuple(arm for arm in EvalArm if self.case_count(arm))

    def case_count(self, arm: EvalArm) -> int:
        return len(self._of(arm))

    def accuracy(self, arm: EvalArm, field: EvalField) -> float | None:
        scored = [result for result in self._of(arm) if result.scored(field)]
        if not scored:
            return None
        return sum(result.passed(field) for result in scored) / len(scored)

    def p50_latency_s(self, arm: EvalArm) -> float | None:
        latencies = [result.latency_s for result in self._of(arm)]
        return statistics.median(latencies) if latencies else None

    def error_count(self, arm: EvalArm) -> int:
        return sum(result.error is not None for result in self._of(arm))

    def _of(self, arm: EvalArm) -> list[CaseResult]:
        return [result for result in self.results if result.arm is arm]
