import pytest
from capture_builders import FORCING_TEXTS, NON_FORCING_TEXTS

from stash.capture import forces_request


@pytest.mark.parametrize("text", FORCING_TEXTS)
def test_a_text_starting_with_a_question_mark_after_whitespace_forces_a_request(
    text: str,
) -> None:
    # Setup
    expected = True

    # Execute
    forced = forces_request(text)

    # Assert
    assert forced is expected


@pytest.mark.parametrize("text", NON_FORCING_TEXTS)
def test_a_text_not_starting_with_a_question_mark_does_not_force_a_request(text: str) -> None:
    # Setup
    expected = False

    # Execute
    forced = forces_request(text)

    # Assert
    assert forced is expected
