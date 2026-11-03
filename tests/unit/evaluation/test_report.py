from eval_builders import a_result

from stash.evaluation import EvalArm, EvalField, EvalRun, render_report

PASS_ALL = {
    "passed_fields": frozenset(EvalField),
    "failed_fields": frozenset(),
}
FAIL_ALL = {
    "passed_fields": frozenset(),
    "failed_fields": frozenset(EvalField),
}


def lines_of(runs: list[EvalRun]) -> list[str]:
    return render_report(runs).splitlines()


def row_of(runs: list[EvalRun], metric: str) -> str:
    return next(line for line in lines_of(runs) if line.startswith(f"| {metric} |"))


def test_the_table_header_names_a_column_for_each_model_label() -> None:
    # Setup
    runs = [EvalRun("local", (a_result(),)), EvalRun("openrouter", (a_result(),))]

    # Execute
    report = render_report(runs)

    # Assert
    assert "| metric | local | openrouter |" in report


def test_the_header_is_followed_by_a_markdown_separator_row() -> None:
    # Setup
    runs = [EvalRun("local", (a_result(),)), EvalRun("openrouter", (a_result(),))]

    # Execute
    lines = lines_of(runs)

    # Assert
    assert lines[lines.index("| metric | local | openrouter |") + 1] == "| --- | --- | --- |"


def test_an_accuracy_cell_is_a_whole_percentage() -> None:
    # Setup
    results = (
        a_result(case_id="a", **PASS_ALL),
        a_result(case_id="b", **PASS_ALL),
        a_result(case_id="c", **FAIL_ALL),
    )

    # Execute
    row = row_of([EvalRun("local", results)], "route accuracy")

    # Assert
    assert row == "| route accuracy | 67% |"


def test_a_field_no_case_scored_shows_not_available() -> None:
    # Execute
    row = row_of([EvalRun("local", (a_result(),))], "date accuracy")

    # Assert
    assert row == "| date accuracy | n/a |"


def test_each_accuracy_row_is_named_for_its_field_in_a_fixed_order() -> None:
    # Execute
    metrics = [
        line.split("|")[1].strip()
        for line in lines_of([EvalRun("local", (a_result(**PASS_ALL),))])
        if "accuracy" in line
    ]

    # Assert
    assert metrics == [
        "route accuracy",
        "type accuracy",
        "stage accuracy",
        "date accuracy",
        "details accuracy",
    ]


def test_the_latency_row_shows_the_p50_in_seconds() -> None:
    # Execute
    row = row_of([EvalRun("local", (a_result(latency_s=1.24),))], "p50 latency")

    # Assert
    assert row == "| p50 latency | 1.2 s |"


def test_the_errors_row_counts_the_errored_cases() -> None:
    # Setup
    results = (a_result(case_id="a", error="OcrError: no OCR"), a_result(case_id="b"))

    # Execute
    row = row_of([EvalRun("local", results)], "errors")

    # Assert
    assert row == "| errors | 1 |"


def test_each_model_column_shows_its_own_numbers() -> None:
    # Setup
    runs = [
        EvalRun("local", (a_result(**FAIL_ALL),)),
        EvalRun("openrouter", (a_result(**PASS_ALL),)),
    ]

    # Execute
    row = row_of(runs, "stage accuracy")

    # Assert
    assert row == "| stage accuracy | 0% | 100% |"


def test_there_is_one_section_per_arm_with_its_case_count_in_arm_order() -> None:
    # Setup
    results = (
        a_result(case_id="a", arm=EvalArm.OCR),
        a_result(case_id="b", arm=EvalArm.TEXT),
        a_result(case_id="c", arm=EvalArm.TEXT),
        a_result(case_id="d", arm=EvalArm.OCR),
        a_result(case_id="e", arm=EvalArm.OCR),
    )

    # Execute
    headings = [line for line in lines_of([EvalRun("local", results)]) if line.startswith("###")]

    # Assert
    assert headings == ["### text arm (2 cases)", "### ocr arm (3 cases)"]


def test_an_arm_no_run_has_results_for_gets_no_section() -> None:
    # Execute
    report = render_report([EvalRun("local", (a_result(arm=EvalArm.TEXT),))])

    # Assert
    assert "vision" not in report


def test_a_run_without_results_for_an_arm_another_run_has_shows_not_available() -> None:
    # Setup
    runs = [
        EvalRun("local", (a_result(arm=EvalArm.OCR),)),
        EvalRun("openrouter", (a_result(arm=EvalArm.TEXT),)),
    ]

    # Execute
    row = row_of(runs, "p50 latency")

    # Assert
    assert row == "| p50 latency | n/a | 1.0 s |"


def test_a_report_without_any_results_says_so_in_one_line() -> None:
    # Execute
    report = render_report([EvalRun("local", ())])

    # Assert
    assert report == "No eval results to report."


def test_a_report_without_runs_says_so_in_one_line() -> None:
    # Execute / Assert
    assert render_report([]) == "No eval results to report."
