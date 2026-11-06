import pytest
from builders import a_capture
from capture_builders import FORCING_TEXTS, NON_FORCING_TEXTS, an_agent_capture

from stash.capture import forces_request, is_forced_request


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


@pytest.mark.parametrize("text", FORCING_TEXTS)
def test_an_agent_capture_starting_with_a_question_mark_is_not_a_forced_request(text: str) -> None:
    # Setup
    capture = an_agent_capture(text=text)

    # Execute
    forced = is_forced_request(capture)

    # Assert
    assert forced is False


@pytest.mark.parametrize("text", FORCING_TEXTS)
def test_a_telegram_capture_starting_with_a_question_mark_is_a_forced_request(text: str) -> None:
    # Setup
    capture = a_capture(text=text)

    # Execute
    forced = is_forced_request(capture)

    # Assert
    assert forced is True


@pytest.mark.parametrize("text", NON_FORCING_TEXTS)
def test_a_telegram_capture_not_starting_with_a_question_mark_is_not_a_forced_request(
    text: str,
) -> None:
    # Setup
    capture = a_capture(text=text)

    # Execute
    forced = is_forced_request(capture)

    # Assert
    assert forced is False
