from collections.abc import Callable, Sequence

from stash.evaluation.expectation import EvalField, FieldMismatch
from stash.evaluation.results import CaseOutcome, CaseResult, EvalArm, EvalRun

NO_RESULTS = "No eval results to report."
NOT_AVAILABLE = "n/a"
CASES_HEADING = "### cases —"
OK_WORD = "ok"
FAIL_WORD = "FAIL"
ERROR_WORD = "ERROR"
FIELD_ROWS = {
    EvalField.ROUTE: "route accuracy",
    EvalField.ITEM_TYPE: "type accuracy",
    EvalField.STAGE: "stage accuracy",
    EvalField.DATE: "date accuracy",
    EvalField.DETAILS: "details accuracy",
}


def render_report(runs: Sequence[EvalRun]) -> str:
    arms = [arm for arm in EvalArm if any(run.case_count(arm) for run in runs)]
    if not arms:
        return NO_RESULTS
    sections = [_section(arm, runs) for arm in arms] + [_cases_section(run) for run in runs]
    return "\n\n".join(sections)


def _section(arm: EvalArm, runs: Sequence[EvalRun]) -> str:
    cases = max(run.case_count(arm) for run in runs)
    lines = [
        f"### {arm.value} arm ({cases} cases)",
        "",
        _row("metric", [run.label for run in runs]),
        _row("---", ["---"] * len(runs)),
        *(_accuracy_row(arm, field, runs) for field in FIELD_ROWS),
        _metric_row("p50 latency", runs, lambda run: _seconds(run.p50_latency_s(arm))),
        _metric_row("errors", runs, lambda run: str(run.error_count(arm))),
    ]
    return "\n".join(lines)


def _cases_section(run: EvalRun) -> str:
    return "\n".join(
        [f"{CASES_HEADING} {run.label}", *(_case_line(result) for result in run.results)]
    )


def _case_line(result: CaseResult) -> str:
    latency = _seconds(result.latency_s)
    prefix = f"{result.case_id} {result.arm.value}"
    match result.outcome:
        case CaseOutcome.OK:
            return f"{prefix} {OK_WORD} ({latency})"
        case CaseOutcome.FAIL:
            return f"{prefix} {FAIL_WORD} {_mismatch_cells(result.mismatches)} ({latency})"
        case CaseOutcome.ERROR:
            return f"{prefix} {ERROR_WORD} {result.error} ({latency})"


def _mismatch_cells(mismatches: Sequence[FieldMismatch]) -> str:
    return "; ".join(
        f"{mismatch.field.value}: want {mismatch.expected} got {mismatch.got}"
        for mismatch in mismatches
    )


def _accuracy_row(arm: EvalArm, field: EvalField, runs: Sequence[EvalRun]) -> str:
    return _metric_row(FIELD_ROWS[field], runs, lambda run: _percent(run.accuracy(arm, field)))


def _metric_row(name: str, runs: Sequence[EvalRun], cell: Callable[[EvalRun], str]) -> str:
    return _row(name, [cell(run) for run in runs])


def _row(first: str, cells: Sequence[str]) -> str:
    return "| " + " | ".join([first, *cells]) + " |"


def _percent(value: float | None) -> str:
    return NOT_AVAILABLE if value is None else f"{value:.0%}"


def _seconds(value: float | None) -> str:
    return NOT_AVAILABLE if value is None else f"{value:.1f} s"
