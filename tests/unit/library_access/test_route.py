import pytest

from stash.library_access import Route, route_of


@pytest.mark.parametrize("target", ["/", "/?k=x", "/?", "/?a=b&k=c", "/?/healthz"])
def test_the_root_path_with_or_without_a_query_is_the_page(target: str) -> None:
    # Execute
    route = route_of(target)

    # Assert
    assert route is Route.PAGE


@pytest.mark.parametrize("target", ["/healthz", "/healthz?k=x", "/healthz?"])
def test_the_healthz_path_with_or_without_a_query_is_the_health_check(target: str) -> None:
    # Execute
    route = route_of(target)

    # Assert
    assert route is Route.HEALTH


@pytest.mark.parametrize(
    "target",
    [
        "",
        "//",
        "//x",
        "/./",
        "/../",
        "/../etc/passwd",
        "/index.html",
        "/healthz/",
        "/healthz/x",
        "/Healthz",
        "/%68ealthz",
        "/ ",
        "http://h/",
        "http://h/healthz",
        "*",
        "healthz",
    ],
)
def test_every_other_target_is_not_found(target: str) -> None:
    # Execute
    route = route_of(target)

    # Assert
    assert route is Route.NOT_FOUND
