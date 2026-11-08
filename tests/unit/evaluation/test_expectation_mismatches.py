from datetime import date

from builders import a_filing
from eval_builders import LONG_MULTILINE_VALUE, an_expectation

from stash.domain import ItemType, Route, Stage
from stash.evaluation import EvalField, FieldMismatch


def test_a_filing_that_agrees_on_every_scored_field_has_no_mismatches() -> None:
    # Setup
    expectation = an_expectation(item_type=ItemType.PLACE, stage=Stage.WANT_TO)

    # Execute
    mismatches = expectation.mismatches(a_filing(item_type=ItemType.PLACE, stage=Stage.WANT_TO))

    # Assert
    assert mismatches == ()


def test_a_planned_and_dated_case_filed_as_want_to_without_a_date_names_both_fields() -> None:
    # Setup
    expectation = an_expectation(stage=Stage.PLANNED, date=date(2027, 3, 14))

    # Execute
    mismatches = expectation.mismatches(a_filing(stage=Stage.WANT_TO, date=None))

    # Assert
    assert mismatches == (
        FieldMismatch(EvalField.STAGE, "planned", "want_to"),
        FieldMismatch(EvalField.DATE, "2027-03-14", "none"),
    )


def test_a_wrong_route_renders_the_route_values() -> None:
    # Execute
    mismatches = an_expectation(route=Route.REQUEST).mismatches(a_filing(route=Route.CAPTURE))

    # Assert
    assert mismatches == (FieldMismatch(EvalField.ROUTE, "request", "capture"),)


def test_a_wrong_item_type_renders_the_item_type_values() -> None:
    # Setup
    expectation = an_expectation(item_type=ItemType.RECIPE)

    # Execute
    mismatches = expectation.mismatches(a_filing(item_type=ItemType.PLACE))

    # Assert
    assert mismatches == (FieldMismatch(EvalField.ITEM_TYPE, "recipe", "place"),)


def test_a_wrong_date_renders_both_dates_in_iso_format() -> None:
    # Setup
    expectation = an_expectation(date=date(2027, 3, 14))

    # Execute
    mismatches = expectation.mismatches(a_filing(date=date(2027, 3, 15)))

    # Assert
    assert mismatches == (FieldMismatch(EvalField.DATE, "2027-03-14", "2027-03-15"),)


def test_mismatches_follow_the_field_declaration_order() -> None:
    # Setup
    expectation = an_expectation(
        route=Route.REQUEST, item_type=ItemType.RECIPE, date=date(2027, 3, 14)
    )

    # Execute
    mismatches = expectation.mismatches(
        a_filing(route=Route.CAPTURE, item_type=ItemType.PLACE, date=None)
    )

    # Assert
    assert [mismatch.field for mismatch in mismatches] == [
        EvalField.ROUTE,
        EvalField.ITEM_TYPE,
        EvalField.DATE,
    ]


def test_a_details_mismatch_shows_key_value_pairs_for_the_expected_keys() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo", "cuisine": "ramen"})
    filing = a_filing(details={"city": "Kyoto", "cuisine": "ramen", "price": "cheap"})

    # Execute
    mismatches = expectation.mismatches(filing)

    # Assert
    assert mismatches == (
        FieldMismatch(EvalField.DETAILS, "city=Tokyo, cuisine=ramen", "city=Kyoto, cuisine=ramen"),
    )


def test_a_details_key_missing_from_the_filing_renders_as_none() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo", "cuisine": "ramen"})

    # Execute
    mismatches = expectation.mismatches(a_filing(details={"cuisine": "ramen"}))

    # Assert
    assert mismatches == (
        FieldMismatch(EvalField.DETAILS, "city=Tokyo, cuisine=ramen", "city=none, cuisine=ramen"),
    )


def test_a_multi_line_filed_detail_renders_on_one_line() -> None:
    # Setup
    expectation = an_expectation(details={"city": "Tokyo"})

    # Execute
    (mismatch,) = expectation.mismatches(a_filing(details={"city": LONG_MULTILINE_VALUE}))

    # Assert
    assert "\n" not in mismatch.got
