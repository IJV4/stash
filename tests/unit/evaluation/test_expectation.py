from datetime import date

import pytest
from builders import a_filing
from eval_builders import an_expectation

from stash.domain import ItemType, Route, Stage
from stash.evaluation import EvalField, FieldVerdict


def test_a_filing_on_the_expected_route_passes_the_route_field() -> None:
    # Execute
    verdict = an_expectation(route=Route.REQUEST).judge(a_filing(route=Route.REQUEST))

    # Assert
    assert verdict == FieldVerdict(frozenset({EvalField.ROUTE}), frozenset())


def test_a_filing_on_another_route_fails_the_route_field() -> None:
    # Execute
    verdict = an_expectation(route=Route.REQUEST).judge(a_filing(route=Route.UNSURE))

    # Assert
    assert verdict == FieldVerdict(frozenset(), frozenset({EvalField.ROUTE}))


def test_the_correct_item_type_passes_the_item_type_field() -> None:
    # Setup
    expectation = an_expectation(item_type=ItemType.RECIPE)

    # Execute
    verdict = expectation.judge(a_filing(item_type=ItemType.RECIPE))

    # Assert
    assert EvalField.ITEM_TYPE in verdict.passed


def test_a_wrong_item_type_fails_the_item_type_field() -> None:
    # Setup
    expectation = an_expectation(item_type=ItemType.RECIPE)

    # Execute
    verdict = expectation.judge(a_filing(item_type=ItemType.PLACE))

    # Assert
    assert EvalField.ITEM_TYPE in verdict.failed


def test_the_correct_stage_passes_the_stage_field() -> None:
    # Setup
    expectation = an_expectation(stage=Stage.WANT_TO)

    # Execute
    verdict = expectation.judge(a_filing(stage=Stage.WANT_TO))

    # Assert
    assert EvalField.STAGE in verdict.passed


def test_a_wrong_stage_fails_the_stage_field() -> None:
    # Setup
    expectation = an_expectation(stage=Stage.WANT_TO)

    # Execute
    verdict = expectation.judge(a_filing(stage=Stage.INBOX))

    # Assert
    assert EvalField.STAGE in verdict.failed


def test_the_expected_date_passes_the_date_field() -> None:
    # Setup
    expectation = an_expectation(date=date(2027, 3, 14))

    # Execute
    verdict = expectation.judge(a_filing(stage=Stage.PLANNED, date=date(2027, 3, 14)))

    # Assert
    assert EvalField.DATE in verdict.passed


def test_another_date_fails_the_date_field() -> None:
    # Setup
    expectation = an_expectation(date=date(2027, 3, 14))

    # Execute
    verdict = expectation.judge(a_filing(stage=Stage.PLANNED, date=date(2027, 3, 15)))

    # Assert
    assert EvalField.DATE in verdict.failed


def test_a_filing_without_a_date_fails_the_date_field() -> None:
    # Setup
    expectation = an_expectation(date=date(2027, 3, 14))

    # Execute
    verdict = expectation.judge(a_filing(date=None))

    # Assert
    assert EvalField.DATE in verdict.failed


def test_an_expected_detail_contained_in_the_filed_value_passes_the_details_field() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo"})

    # Execute
    verdict = expectation.judge(a_filing(details={"city": "Shibuya, Tokyo"}))

    # Assert
    assert EvalField.DETAILS in verdict.passed


def test_details_are_compared_ignoring_case() -> None:
    # Setup
    expectation = an_expectation(details={"city": "TOKYO"})

    # Execute
    verdict = expectation.judge(a_filing(details={"city": "tokyo"}))

    # Assert
    assert EvalField.DETAILS in verdict.passed


def test_a_filed_value_that_lacks_the_expected_text_fails_the_details_field() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo"})

    # Execute
    verdict = expectation.judge(a_filing(details={"city": "Lisbon"}))

    # Assert
    assert EvalField.DETAILS in verdict.failed


def test_a_missing_detail_key_fails_the_details_field() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo"})

    # Execute
    verdict = expectation.judge(a_filing(details={"author": "Tokyo"}))

    # Assert
    assert EvalField.DETAILS in verdict.failed


def test_every_expected_detail_must_match_for_the_details_field_to_pass() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo", "author": "Powers"})

    # Execute
    verdict = expectation.judge(a_filing(details={"city": "Tokyo"}))

    # Assert
    assert EvalField.DETAILS in verdict.failed


def test_fields_the_expectation_leaves_out_are_neither_passed_nor_failed() -> None:
    # Execute
    verdict = an_expectation().judge(a_filing(item_type=ItemType.BOOK, stage=Stage.DONE))

    # Assert
    assert verdict.passed | verdict.failed == {EvalField.ROUTE}


def test_an_expectation_scores_only_the_fields_it_states() -> None:
    # Setup
    expectation = an_expectation(stage=Stage.WANT_TO, details={"city": "Tokyo"})

    # Execute
    scored = expectation.scored_fields()

    # Assert
    assert scored == {EvalField.ROUTE, EvalField.STAGE, EvalField.DETAILS}


def test_an_expectation_with_every_field_scores_all_five() -> None:
    # Setup
    expectation = an_expectation(
        item_type=ItemType.PLACE,
        stage=Stage.PLANNED,
        date=date(2027, 3, 14),
        details={"city": "Tokyo"},
    )

    # Execute
    scored = expectation.scored_fields()

    # Assert
    assert scored == set(EvalField)


def test_expected_details_cannot_be_changed_afterwards() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo"})

    # Execute / Assert
    with pytest.raises(TypeError):
        expectation.details["city"] = "Lisbon"


def test_expected_details_are_copied_from_the_mapping_given() -> None:
    # Setup
    given = {"city": "Tokyo"}
    expectation = an_expectation(details=given)

    # Execute
    given["city"] = "Lisbon"

    # Assert
    assert expectation.details == {"city": "Tokyo"}


def test_a_verdict_in_which_every_scored_field_failed_lists_them_all_as_failed() -> None:
    # Setup
    scored = frozenset({EvalField.ROUTE, EvalField.STAGE})

    # Execute
    verdict = FieldVerdict.all_failed(scored)

    # Assert
    assert verdict == FieldVerdict(frozenset(), scored)


def test_a_verdict_cannot_pass_and_fail_the_same_field() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="both passed and failed"):
        FieldVerdict(frozenset({EvalField.ROUTE}), frozenset({EvalField.ROUTE}))


def test_the_field_names_are_the_words_used_in_reports() -> None:
    # Assert
    assert [field.value for field in EvalField] == [
        "route",
        "item_type",
        "stage",
        "date",
        "details",
    ]
