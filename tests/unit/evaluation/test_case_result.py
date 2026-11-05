import pytest
from eval_builders import HOSTILE_TEXTS, HostileText, a_mismatch, a_result

from stash.evaluation import CaseOutcome, CaseResult, EvalArm, EvalField
from stash.evaluation.results import ERROR_LIMIT

FAIL_STAGE = {"passed_fields": frozenset(), "failed_fields": frozenset({EvalField.STAGE})}


def test_a_result_without_mismatches_defaults_to_an_empty_tuple() -> None:
    # Execute
    result = a_result()

    # Assert
    assert result.mismatches == ()


def test_the_mismatches_are_stored_as_a_tuple() -> None:
    # Setup
    mismatch = a_mismatch(EvalField.STAGE)

    # Execute
    result = a_result(mismatches=[mismatch], **FAIL_STAGE)

    # Assert
    assert result.mismatches == (mismatch,)


def test_a_failed_field_without_a_mismatch_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="mismatches"):
        CaseResult(
            case_id="t01",
            arm=EvalArm.TEXT,
            passed_fields=frozenset(),
            failed_fields=frozenset({EvalField.STAGE}),
            latency_s=1.0,
            error=None,
        )


def test_a_mismatch_on_a_field_that_did_not_fail_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="mismatches"):
        a_result(
            passed_fields=frozenset({EvalField.STAGE}),
            failed_fields=frozenset(),
            mismatches=(a_mismatch(EvalField.STAGE),),
        )


def test_an_errored_result_with_mismatches_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="error"):
        a_result(
            error="LlmUnavailable: down",
            mismatches=(a_mismatch(EvalField.STAGE),),
            **FAIL_STAGE,
        )


def test_an_errored_result_without_mismatches_is_accepted() -> None:
    # Execute
    result = a_result(error="LlmUnavailable: down", **FAIL_STAGE)

    # Assert
    assert result.mismatches == ()


def test_a_result_with_no_failed_field_and_no_error_is_ok() -> None:
    # Execute
    outcome = a_result().outcome

    # Assert
    assert outcome is CaseOutcome.OK


def test_a_result_with_a_failed_field_is_a_fail() -> None:
    # Execute
    outcome = a_result(**FAIL_STAGE).outcome

    # Assert
    assert outcome is CaseOutcome.FAIL


def test_a_result_with_an_error_is_an_error_even_though_its_fields_failed() -> None:
    # Execute
    outcome = a_result(error="boom", **FAIL_STAGE).outcome

    # Assert
    assert outcome is CaseOutcome.ERROR


def test_a_long_multi_line_error_becomes_one_line_of_two_hundred_characters() -> None:
    # Setup
    error = ("boom with detail\n" * 300)[:5000]

    # Execute
    result = a_result(error=error, **FAIL_STAGE)

    # Assert
    assert result.error == ("boom with detail " * 12)[:200]


@pytest.mark.parametrize("hostile", HOSTILE_TEXTS)
def test_an_error_with_unprintable_characters_is_stored_with_them_replaced_and_clipped(
    hostile: HostileText,
) -> None:
    # Execute
    result = a_result(error=hostile.padded_beyond(ERROR_LIMIT), **FAIL_STAGE)

    # Assert
    assert result.error == hostile.sanitised_and_clipped_to(ERROR_LIMIT)
