import pytest

from stash.library_access import LibraryAccess

TOKEN = "Ab3-._~Ab3-._~Ab3-._~Ab3-"
OTHER = "Zz9-._~Zz9-._~Zz9-._~Zz9-"
COOKIE = f"stash_k={TOKEN}; HttpOnly; SameSite=Strict; Path=/"


def admission(target: str, cookie: str | None = None):
    return LibraryAccess(TOKEN).admit(target, cookie)


def test_the_token_in_the_query_is_admitted() -> None:
    # Execute
    granted = admission(f"/?k={TOKEN}").granted

    # Assert
    assert granted is True


def test_the_token_in_the_query_asks_for_the_exact_cookie() -> None:
    # Execute
    set_cookie = admission(f"/?k={TOKEN}").set_cookie

    # Assert
    assert set_cookie == COOKIE


def test_the_token_in_the_cookie_is_admitted() -> None:
    # Execute
    granted = admission("/", f"stash_k={TOKEN}").granted

    # Assert
    assert granted is True


def test_the_token_in_the_cookie_alone_sets_no_cookie() -> None:
    # Execute
    set_cookie = admission("/", f"stash_k={TOKEN}").set_cookie

    # Assert
    assert set_cookie is None


def test_a_cookie_among_other_cookies_with_junk_pieces_is_admitted() -> None:
    # Execute
    granted = admission("/", f"junk; =; a=b;stash_k = {TOKEN} ;;x").granted

    # Assert
    assert granted is True


def test_a_percent_encoded_token_in_the_query_is_admitted() -> None:
    # Execute
    granted = admission(f"/?k={TOKEN.replace('A', '%41')}").granted

    # Assert
    assert granted is True


def test_any_matching_value_among_repeated_query_parameters_is_admitted() -> None:
    # Execute
    granted = admission(f"/?k={OTHER}&k={TOKEN}").granted

    # Assert
    assert granted is True


def test_a_matching_query_token_wins_over_a_wrong_cookie_and_sets_the_cookie() -> None:
    # Execute
    set_cookie = admission(f"/?k={TOKEN}", f"stash_k={OTHER}").set_cookie

    # Assert
    assert set_cookie == COOKIE


@pytest.mark.parametrize(
    ("target", "cookie"),
    [
        ("/", None),
        ("/?", None),
        (f"/?k={OTHER}", None),
        ("/?k=", None),
        (f"/?k={TOKEN[:-1]}", None),
        (f"/?k={TOKEN}x", None),
        (f"/?K={TOKEN}", None),
        (f"/?key={TOKEN}", None),
        ("/?k=%C3%A9", None),
        (f"/?k={TOKEN}%C3%A9", None),
        ("/?k=é", None),
        ("/", f"stash_k={OTHER}"),
        ("/", "stash_k="),
        ("/", "stash_k=é"),
        ("/", f"other={TOKEN}"),
        ("/", f"{TOKEN}"),
        ("/", f"xstash_k={TOKEN}"),
    ],
)
def test_a_wrong_missing_malformed_or_non_ascii_token_is_denied(
    target: str, cookie: str | None
) -> None:
    # Execute
    granted = admission(target, cookie).granted

    # Assert
    assert granted is False


def test_too_many_query_fields_are_denied_even_with_the_right_cookie() -> None:
    # Setup
    crowded = "/?" + "&".join(["a=b"] * 50)

    # Execute
    granted = admission(crowded, f"stash_k={TOKEN}").granted

    # Assert
    assert granted is False


def test_a_denied_request_asks_for_no_cookie() -> None:
    # Execute
    set_cookie = admission(f"/?k={OTHER}").set_cookie

    # Assert
    assert set_cookie is None


def test_the_cookie_to_set_never_appears_in_the_repr_of_the_admission() -> None:
    # Execute
    shown = repr(admission(f"/?k={TOKEN}"))

    # Assert
    assert TOKEN not in shown
