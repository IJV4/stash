import pytest
from eval_builders import a_result

from stash.evaluation import EvalArm, EvalField, EvalRun

PASS_STAGE = {"passed_fields": frozenset({EvalField.STAGE}), "failed_fields": frozenset()}
FAIL_STAGE = {"passed_fields": frozenset(), "failed_fields": frozenset({EvalField.STAGE})}


def test_the_arms_are_text_vision_and_ocr() -> None:
    # Assert
    assert [arm.value for arm in EvalArm] == ["text", "vision", "ocr"]


def test_accuracy_is_the_share_of_scoring_cases_that_passed_the_field() -> None:
    # Setup
    run = EvalRun(
        "local",
        (
            a_result(case_id="a", **PASS_STAGE),
            a_result(case_id="b", **PASS_STAGE),
            a_result(case_id="c", **FAIL_STAGE),
            a_result(case_id="d", **FAIL_STAGE),
        ),
    )

    # Execute
    accuracy = run.accuracy(EvalArm.TEXT, EvalField.STAGE)

    # Assert
    assert accuracy == 0.5


def test_cases_that_did_not_score_the_field_do_not_count_toward_its_accuracy() -> None:
    # Setup
    run = EvalRun("local", (a_result(case_id="a", **PASS_STAGE), a_result(case_id="b")))

    # Execute
    accuracy = run.accuracy(EvalArm.TEXT, EvalField.STAGE)

    # Assert
    assert accuracy == 1.0


def test_accuracy_is_unknown_when_no_case_scored_the_field() -> None:
    # Setup
    run = EvalRun("local", (a_result(),))

    # Execute
    accuracy = run.accuracy(EvalArm.TEXT, EvalField.DATE)

    # Assert
    assert accuracy is None


def test_accuracy_counts_only_the_cases_of_the_arm_asked_about() -> None:
    # Setup
    run = EvalRun(
        "local",
        (a_result(arm=EvalArm.TEXT, **PASS_STAGE), a_result(arm=EvalArm.OCR, **FAIL_STAGE)),
    )

    # Execute
    accuracy = run.accuracy(EvalArm.OCR, EvalField.STAGE)

    # Assert
    assert accuracy == 0.0


def test_an_errored_case_counts_as_a_failure_in_the_accuracy() -> None:
    # Setup
    errored = a_result(case_id="b", error="LlmUnavailable: down", **FAIL_STAGE)
    run = EvalRun("local", (a_result(case_id="a", **PASS_STAGE), errored))

    # Execute
    accuracy = run.accuracy(EvalArm.TEXT, EvalField.STAGE)

    # Assert
    assert accuracy == 0.5


def test_the_p50_latency_is_the_middle_latency_of_the_arm() -> None:
    # Setup
    run = EvalRun("local", tuple(a_result(case_id=str(n), latency_s=n) for n in (9.0, 1.0, 2.0)))

    # Execute
    latency = run.p50_latency_s(EvalArm.TEXT)

    # Assert
    assert latency == 2.0


def test_the_p50_latency_of_an_even_number_of_cases_is_the_mean_of_the_middle_two() -> None:
    # Setup
    run = EvalRun(
        "local", tuple(a_result(case_id=str(n), latency_s=n) for n in (1.0, 2.0, 4.0, 9.0))
    )

    # Execute
    latency = run.p50_latency_s(EvalArm.TEXT)

    # Assert
    assert latency == 3.0


def test_the_p50_latency_is_unknown_for_an_arm_without_results() -> None:
    # Setup
    run = EvalRun("local", (a_result(arm=EvalArm.TEXT),))

    # Execute
    latency = run.p50_latency_s(EvalArm.VISION)

    # Assert
    assert latency is None


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


def test_the_case_count_is_the_number_of_results_of_the_arm() -> None:
    # Setup
    run = EvalRun("local", (a_result(case_id="a"), a_result(case_id="b", arm=EvalArm.OCR)))

    # Execute
    count = run.case_count(EvalArm.TEXT)

    # Assert
    assert count == 1


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


def test_a_run_keeps_its_results_as_a_tuple_even_when_given_a_list() -> None:
    # Execute
    run = EvalRun("local", [a_result()])

    # Assert
    assert isinstance(run.results, tuple)


def test_a_result_scored_a_field_it_passed() -> None:
    # Execute / Assert
    assert a_result(**PASS_STAGE).scored(EvalField.STAGE) is True


def test_a_result_scored_a_field_it_failed() -> None:
    # Execute / Assert
    assert a_result(**FAIL_STAGE).scored(EvalField.STAGE) is True


def test_a_result_did_not_score_a_field_it_neither_passed_nor_failed() -> None:
    # Execute / Assert
    assert a_result(**PASS_STAGE).scored(EvalField.DATE) is False


def test_a_result_passed_a_field_it_passed() -> None:
    # Execute / Assert
    assert a_result(**PASS_STAGE).passed(EvalField.STAGE) is True


def test_a_result_did_not_pass_a_field_it_failed() -> None:
    # Execute / Assert
    assert a_result(**FAIL_STAGE).passed(EvalField.STAGE) is False


def test_a_result_did_not_pass_a_field_it_did_not_score() -> None:
    # Execute / Assert
    assert a_result().passed(EvalField.STAGE) is False
