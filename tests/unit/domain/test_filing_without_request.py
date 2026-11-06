import pytest
from builders import a_filing

from stash.domain import Route


def test_a_request_filing_without_the_request_becomes_unsure() -> None:
    # Setup
    filing = a_filing(route=Route.REQUEST)

    # Execute
    unsure = filing.without_request()

    # Assert
    assert unsure.route is Route.UNSURE


@pytest.mark.parametrize("route", [Route.CAPTURE, Route.UNSURE])
def test_a_filing_that_is_not_a_request_keeps_its_route_without_the_request(route: Route) -> None:
    # Setup
    filing = a_filing(route=route)

    # Execute
    kept = filing.without_request()

    # Assert
    assert kept.route is route


def test_a_request_filing_without_the_request_keeps_everything_else() -> None:
    # Setup
    filing = a_filing(route=Route.REQUEST, tags=("ramen",))

    # Execute
    unsure = filing.without_request()

    # Assert
    assert unsure == a_filing(route=Route.UNSURE, tags=("ramen",))
