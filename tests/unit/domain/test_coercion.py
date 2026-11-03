import pytest

from stash.domain import Stage, enum_member

ALLOWED = (Stage.INBOX, Stage.WANT_TO)


def test_a_string_naming_a_member_becomes_that_member() -> None:
    # Execute / Assert
    assert enum_member(Stage, "doing") is Stage.DOING


def test_a_string_naming_no_member_becomes_none() -> None:
    # Execute / Assert
    assert enum_member(Stage, "limbo") is None


@pytest.mark.parametrize("value", [None, 3, ["doing"], b"doing", Stage])
def test_a_value_that_is_not_a_string_becomes_none(value: object) -> None:
    # Execute / Assert
    assert enum_member(Stage, value) is None


def test_a_member_inside_the_allow_list_is_kept() -> None:
    # Execute / Assert
    assert enum_member(Stage, "want_to", ALLOWED) is Stage.WANT_TO


def test_a_member_outside_the_allow_list_becomes_none() -> None:
    # Execute / Assert
    assert enum_member(Stage, "doing", ALLOWED) is None


def test_an_empty_allow_list_allows_nothing() -> None:
    # Execute / Assert
    assert enum_member(Stage, "inbox", ()) is None
