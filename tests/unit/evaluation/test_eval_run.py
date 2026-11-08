import pytest
from eval_builders import a_result

from stash.evaluation import EvalArm, EvalField, EvalRun

PASS_STAGE = {"passed_fields": frozenset({EvalField.STAGE}), "failed_fields": frozenset()}
FAIL_STAGE = {"passed_fields": frozenset(), "failed_fields": frozenset({EvalField.STAGE})}


def test_the_arms_are_text_vision_and_ocr() -> None:
    # Assert
    assert [arm.value for arm in EvalArm] == ["text", "vision", "ocr"]


def test_an_errored_case_counts_as_a_failure_in_the_accuracy() -> None:
    # Setup
    errored = a_result(case_id="b", error="LlmUnavailable: down", **FAIL_STAGE)
    run = EvalRun("local", (a_result(case_id="a", **PASS_STAGE), errored))

    # Execute
    accuracy = run.accuracy(EvalArm.TEXT, EvalField.STAGE)

    # Assert
    assert accuracy == 0.5


def test_the_error_count_counts_the_errored_cases_of_the_arm() -> None:
    # Setup
    run = EvalRun(
        "local",
        (
            a_result(case_id="a", error="OcrError: no OCR"),
            a_result(case_id="b"),
            a_result(case_id="c", arm=EvalArm.OCR, error="OcrError: no OCR"),
        ),
    )

    # Execute
    errors = run.error_count(EvalArm.TEXT)

    # Assert
    assert errors == 1


def test_the_arms_with_results_are_listed_in_the_fixed_arm_order() -> None:
    # Setup
    run = EvalRun(
        "local",
        (
            a_result(case_id="a", arm=EvalArm.OCR),
            a_result(case_id="b", arm=EvalArm.TEXT),
            a_result(case_id="c", arm=EvalArm.OCR),
        ),
    )

    # Execute
    arms = run.arms()

    # Assert
    assert arms == (EvalArm.TEXT, EvalArm.OCR)


def test_a_run_without_results_has_no_arms() -> None:
    # Execute / Assert
    assert EvalRun("local", ()).arms() == ()


def test_a_run_with_a_blank_label_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="label must not be blank"):
        EvalRun(" ", ())
