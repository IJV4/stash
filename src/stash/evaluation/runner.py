import datetime as dt
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from zoneinfo import ZoneInfo

from stash.domain import describe_failure
from stash.evaluation.arms import Arm, build_arms
from stash.evaluation.cases import EvalCase
from stash.evaluation.expectation import FieldMismatch, FieldVerdict
from stash.evaluation.ocr import Ocr, OcrError
from stash.evaluation.results import CaseResult, EvalArm, EvalRun
from stash.evaluation.target import EvalTarget
from stash.llm import LlmError


def run_eval(
    cases: Sequence[EvalCase],
    target: EvalTarget,
    arms: Sequence[EvalArm],
    ocr: Ocr,
    clock: Callable[[], dt.datetime],
    *,
    timezone: ZoneInfo,
    timer: Callable[[], float] = time.perf_counter,
    read_image: Callable[[Path], bytes] = Path.read_bytes,
) -> EvalRun:
    results = tuple(
        _run_case(arm, case, timer)
        for arm in build_arms(arms, target, ocr, clock, timezone, read_image)
        for case in cases
        if arm.applies_to(case)
    )
    return EvalRun(target.label, results)


def evaluate(
    cases: Sequence[EvalCase],
    targets: Sequence[EvalTarget],
    arms: Sequence[EvalArm],
    ocr: Ocr,
    clock: Callable[[], dt.datetime],
    *,
    timezone: ZoneInfo,
    timer: Callable[[], float] = time.perf_counter,
    read_image: Callable[[Path], bytes] = Path.read_bytes,
) -> list[EvalRun]:
    return [
        run_eval(
            cases, target, arms, ocr, clock, timer=timer, read_image=read_image, timezone=timezone
        )
        for target in targets
    ]


def _run_case(arm: Arm, case: EvalCase, timer: Callable[[], float]) -> CaseResult:
    started = timer()
    try:
        filing = arm.file(case)
    except (LlmError, OcrError, OSError, ValueError) as failure:
        verdict = FieldVerdict.all_failed(case.expect.scored_fields())
        return _result(arm, case, verdict, timer() - started, error=describe_failure(failure))
    assessment = case.expect.assess(filing)
    return _result(
        arm, case, assessment.verdict, timer() - started, mismatches=assessment.mismatches
    )


def _result(
    arm: Arm,
    case: EvalCase,
    verdict: FieldVerdict,
    latency_s: float,
    *,
    error: str | None = None,
    mismatches: tuple[FieldMismatch, ...] = (),
) -> CaseResult:
    return CaseResult(
        case_id=case.id,
        arm=arm.kind,
        passed_fields=verdict.passed,
        failed_fields=verdict.failed,
        latency_s=latency_s,
        error=error,
        mismatches=mismatches,
    )
