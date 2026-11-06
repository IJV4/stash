import pytest
from planning_builders import a_raw_step

from stash.domain import STEP_TEXT_LIMIT
from stash.planning import parse_steps

NOT_A_LIST = ["Book the table", {"text": "Book the table"}, None, 3]
NOT_A_DICT = ["Book the table", 3, None, ["Book the table", 7]]
NOT_A_STRING = [None, 3, ["Book"], {"a": "b"}, True]


def texts_of(*entries: object) -> list[str]:
    return [step.text for step in parse_steps({"steps": list(entries)})]


def test_an_answer_without_steps_proposes_nothing() -> None:
    # Execute
    steps = parse_steps({})

    # Assert
    assert steps == ()


@pytest.mark.parametrize("value", NOT_A_LIST, ids=repr)
def test_an_answer_whose_steps_are_not_a_list_proposes_nothing(value: object) -> None:
    # Execute
    steps = parse_steps({"steps": value})

    # Assert
    assert steps == ()


def test_an_empty_list_of_steps_proposes_nothing() -> None:
    # Execute
    steps = parse_steps({"steps": []})

    # Assert
    assert steps == ()


@pytest.mark.parametrize("entry", NOT_A_DICT, ids=repr)
def test_an_entry_that_is_not_an_object_is_skipped(entry: object) -> None:
    # Execute
    texts = texts_of(entry, a_raw_step(text="Book the table"))

    # Assert
    assert texts == ["Book the table"]


@pytest.mark.parametrize("value", NOT_A_STRING, ids=repr)
def test_an_entry_whose_text_is_not_a_string_is_skipped(value: object) -> None:
    # Execute
    texts = texts_of(a_raw_step(text=value), a_raw_step(text="Book the table"))

    # Assert
    assert texts == ["Book the table"]


def test_an_entry_without_text_is_skipped() -> None:
    # Execute
    texts = texts_of({"lead_days": 7}, a_raw_step(text="Book the table"))

    # Assert
    assert texts == ["Book the table"]


def test_non_printable_characters_in_the_text_become_single_spaces() -> None:
    # Execute
    texts = texts_of(a_raw_step(text="Book\x00 the\t\x07table"))

    # Assert
    assert texts == ["Book the table"]


def test_surrounding_whitespace_is_trimmed() -> None:
    # Execute
    texts = texts_of(a_raw_step(text="  Book the table \n"))

    # Assert
    assert texts == ["Book the table"]


@pytest.mark.parametrize("blank", ["", "   ", "\x00\x01\x02", "\n\t"], ids=repr)
def test_an_entry_whose_text_is_blank_after_cleaning_is_skipped(blank: str) -> None:
    # Execute
    texts = texts_of(a_raw_step(text=blank), a_raw_step(text="Book the table"))

    # Assert
    assert texts == ["Book the table"]


def test_a_two_kilobyte_text_is_clipped_to_the_step_text_limit() -> None:
    # Execute
    texts = texts_of(a_raw_step(text="x" * 2048))

    # Assert
    assert [len(text) for text in texts] == [STEP_TEXT_LIMIT]


def test_a_text_of_exactly_the_limit_is_kept_whole() -> None:
    # Execute
    texts = texts_of(a_raw_step(text="y" * STEP_TEXT_LIMIT))

    # Assert
    assert texts == ["y" * STEP_TEXT_LIMIT]


def test_a_position_supplied_by_the_model_is_ignored() -> None:
    # Execute
    steps = parse_steps({"steps": [a_raw_step(position=99, id="s9", confirmed=True)]})

    # Assert
    assert [(step.text, step.lead_days) for step in steps] == [("Book the table", 7)]


def test_steps_keep_the_models_order() -> None:
    # Execute
    texts = texts_of(a_raw_step(text="First"), a_raw_step(text="Second"), a_raw_step(text="Third"))

    # Assert
    assert texts == ["First", "Second", "Third"]
