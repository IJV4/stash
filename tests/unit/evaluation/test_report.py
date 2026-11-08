from eval_builders import a_result

from stash.evaluation import EvalRun, render_report


def lines_of(runs: list[EvalRun]) -> list[str]:
    return render_report(runs).splitlines()


def row_of(runs: list[EvalRun], metric: str) -> str:
    return next(line for line in lines_of(runs) if line.startswith(f"| {metric} |"))


def test_the_errors_row_counts_the_errored_cases() -> None:
    # Setup
    results = (a_result(case_id="a", error="OcrError: no OCR"), a_result(case_id="b"))

    # Execute
    row = row_of([EvalRun("local", results)], "errors")

    # Assert
    assert row == "| errors | 1 |"


def test_a_report_without_any_results_says_so_in_one_line() -> None:
    # Execute
    report = render_report([EvalRun("local", ())])

    # Assert
    assert report == "No eval results to report."


def test_a_report_without_runs_says_so_in_one_line() -> None:
    # Execute / Assert
    assert render_report([]) == "No eval results to report."
