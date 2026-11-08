from eval_builders import a_result

from stash.evaluation import EvalArm, EvalField, EvalRun, render_report
from stash.evaluation.report import CASES_HEADING, CODE_FENCE

HEADING_AND_OPENING_FENCE = 2


def cases_tail_of(runs: list[EvalRun]) -> list[str]:
    lines = render_report(runs).splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(CASES_HEADING))
    return lines[start:]


def section_of(runs: list[EvalRun]) -> list[str]:
    tail = cases_tail_of(runs)
    closing_fence = tail.index(CODE_FENCE, HEADING_AND_OPENING_FENCE)
    return tail[: closing_fence + 1]


def case_lines_of(runs: list[EvalRun]) -> list[str]:
    return section_of(runs)[HEADING_AND_OPENING_FENCE:-1]


def test_an_errored_case_shows_its_error_text() -> None:
    # Setup
    result = a_result(
        case_id="i02",
        arm=EvalArm.VISION,
        latency_s=0.0,
        passed_fields=frozenset(),
        failed_fields=frozenset({EvalField.ROUTE}),
        error="LlmUnavailable: ollama unreachable: ConnectError",
    )

    # Execute
    line = case_lines_of([EvalRun("local", (result,))])[0]

    # Assert
    assert line == "i02 vision ERROR LlmUnavailable: ollama unreachable: ConnectError (0.0 s)"
