from eval_builders import LONG_MULTILINE_VALUE, a_mismatch, a_result, a_text_case, an_image_case
from eval_rig import run_cases

from stash.evaluation import EvalArm, EvalField, EvalRun, render_report
from stash.evaluation.report import CASES_HEADING, CODE_FENCE

STAGE_AND_DATE_FAIL = {
    "passed_fields": frozenset(),
    "failed_fields": frozenset({EvalField.STAGE, EvalField.DATE}),
    "mismatches": (
        a_mismatch(EvalField.STAGE, "planned", "want_to"),
        a_mismatch(EvalField.DATE, "2027-03-14", "none"),
    ),
}


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


def test_a_passing_case_is_listed_with_its_arm_and_latency() -> None:
    # Setup
    run = EvalRun("local", (a_result(case_id="t01", latency_s=1.0),))

    # Execute
    lines = section_of([run])

    # Assert
    assert lines == ["### cases — local", CODE_FENCE, "t01 text ok (1.0 s)", CODE_FENCE]


def test_a_failing_case_lists_each_failed_field_with_what_was_wanted_and_got() -> None:
    # Setup
    run = EvalRun("local", (a_result(case_id="t10", latency_s=0.3, **STAGE_AND_DATE_FAIL),))

    # Execute
    line = case_lines_of([run])[0]

    # Assert
    assert line == (
        "t10 text FAIL stage: want planned got want_to; date: want 2027-03-14 got none (0.3 s)"
    )


def test_a_failing_case_names_the_field_by_its_report_value() -> None:
    # Setup
    result = a_result(
        passed_fields=frozenset(),
        failed_fields=frozenset({EvalField.ITEM_TYPE}),
        mismatches=(a_mismatch(EvalField.ITEM_TYPE, "recipe", "place"),),
    )

    # Execute
    line = case_lines_of([EvalRun("local", (result,))])[0]

    # Assert
    assert line == "t01 text FAIL item_type: want recipe got place (1.0 s)"


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


def test_each_run_gets_a_cases_section_headed_by_its_label_in_run_order() -> None:
    # Setup
    runs = [EvalRun("local", (a_result(),)), EvalRun("openrouter", (a_result(),))]

    # Execute
    headings = [line for line in render_report(runs).splitlines() if line.startswith("### cases")]

    # Assert
    assert headings == ["### cases — local", "### cases — openrouter"]


def test_cases_are_listed_in_result_order_not_grouped_by_arm() -> None:
    # Setup
    results = (
        a_result(case_id="b", arm=EvalArm.OCR),
        a_result(case_id="a", arm=EvalArm.TEXT),
        a_result(case_id="c", arm=EvalArm.OCR),
    )

    # Execute
    lines = case_lines_of([EvalRun("local", results)])

    # Assert
    assert [line.split()[0] for line in lines] == ["b", "a", "c"]


def test_the_cases_sections_follow_the_arm_tables_after_a_blank_line() -> None:
    # Setup
    run = EvalRun("local", (a_result(),))

    # Execute
    lines = render_report([run]).splitlines()

    # Assert
    assert lines[lines.index("### cases — local") - 1] == ""


def test_a_long_multi_line_model_value_still_yields_one_report_line_for_the_case() -> None:
    # Setup
    result = a_result(
        passed_fields=frozenset(),
        failed_fields=frozenset({EvalField.DETAILS}),
        mismatches=(a_mismatch(EvalField.DETAILS, "city=Tokyo", LONG_MULTILINE_VALUE),),
    )

    # Execute
    lines = case_lines_of([EvalRun("local", (result,))])

    # Assert
    assert len(lines) == 1


def test_a_run_over_mixed_cases_lists_them_by_arm_then_in_file_order_within_each_arm() -> None:
    # Setup
    cases = [a_text_case(id="t01"), an_image_case(id="i01"), a_text_case(id="t02")]
    run = run_cases(cases, arms=(EvalArm.TEXT, EvalArm.VISION))

    # Execute
    lines = case_lines_of([run])

    # Assert
    assert [line.split()[0] for line in lines] == ["t01", "t02", "i01"]


def test_a_run_over_mixed_cases_lists_the_arms_in_the_order_they_were_requested() -> None:
    # Setup
    cases = [a_text_case(id="t01"), an_image_case(id="i01"), a_text_case(id="t02")]
    run = run_cases(cases, arms=(EvalArm.OCR, EvalArm.TEXT))

    # Execute
    lines = case_lines_of([run])

    # Assert
    assert [line.split()[0] for line in lines] == ["i01", "t01", "t02"]


def test_each_runs_case_lines_are_wrapped_in_their_own_code_fence() -> None:
    # Setup
    runs = [
        EvalRun("local", (a_result(case_id="t01", latency_s=1.0),)),
        EvalRun("openrouter", (a_result(case_id="t02", latency_s=2.0),)),
    ]

    # Execute
    lines = cases_tail_of(runs)

    # Assert
    assert lines == [
        "### cases — local",
        CODE_FENCE,
        "t01 text ok (1.0 s)",
        CODE_FENCE,
        "",
        "### cases — openrouter",
        CODE_FENCE,
        "t02 text ok (2.0 s)",
        CODE_FENCE,
    ]
