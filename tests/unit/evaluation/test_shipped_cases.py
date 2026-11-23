from collections import Counter

from eval_files import SHIPPED_CASES

from stash.domain import Route
from stash.evaluation import CaseKind, EvalCase, EvalField, load_cases


def shipped_cases() -> list[EvalCase]:
    return load_cases(SHIPPED_CASES)


def is_text_filing(case: EvalCase) -> bool:
    return case.kind is CaseKind.TEXT and case.expect.scored_fields() != {EvalField.ROUTE}


def is_text_routing(case: EvalCase) -> bool:
    return case.kind is CaseKind.TEXT and case.expect.scored_fields() == {EvalField.ROUTE}


def test_nineteen_shipped_text_cases_are_filings() -> None:
    # Execute
    filings = [case for case in shipped_cases() if is_text_filing(case)]

    # Assert
    assert len(filings) == 19


def test_twenty_two_shipped_text_cases_are_routing_cases_scored_on_route_only() -> None:
    # Execute
    routing = [case for case in shipped_cases() if is_text_routing(case)]

    # Assert
    assert len(routing) == 22


def test_the_shipped_routing_cases_expect_four_requests_nine_unsure_and_nine_captures() -> None:
    # Execute
    routes = Counter(case.expect.route for case in shipped_cases() if is_text_routing(case))

    # Assert
    assert routes == {Route.REQUEST: 4, Route.UNSURE: 9, Route.CAPTURE: 9}
