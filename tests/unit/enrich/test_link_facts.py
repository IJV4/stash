from dataclasses import replace

import pytest
from link_builders import KNIFE_SKILLS_FACTS, a_knife_skills_link, a_link_info

from stash.domain import DETAIL_VALUE_LIMIT
from stash.enrich.links import LinkInfo

LONG_TEXT = "word " * 10_000


def test_a_link_with_title_uploader_and_duration_states_all_three_as_facts() -> None:
    # Setup
    info = a_knife_skills_link()

    # Execute
    facts = info.facts()

    # Assert
    assert facts == KNIFE_SKILLS_FACTS


def test_a_link_nothing_is_known_about_states_no_facts() -> None:
    # Setup
    info = LinkInfo.unknown("https://www.youtube.com/watch?v=abc123")

    # Execute
    facts = info.facts()

    # Assert
    assert facts == {}


@pytest.mark.parametrize(
    ("unknown_field", "left_out"),
    [("title", "link_title"), ("uploader", "uploader"), ("duration_s", "duration")],
)
def test_a_fact_that_is_not_known_is_left_out(unknown_field: str, left_out: str) -> None:
    # Setup
    info = replace(a_knife_skills_link(), **{unknown_field: None})

    # Execute
    facts = info.facts()

    # Assert
    assert facts == {name: text for name, text in KNIFE_SKILLS_FACTS.items() if name != left_out}


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [
        (0, "0:00"),
        (9, "0:09"),
        (59, "0:59"),
        (60, "1:00"),
        (754, "12:34"),
        (3599, "59:59"),
        (3600, "1:00:00"),
        (3723, "1:02:03"),
        (36000, "10:00:00"),
        (360000, "100:00:00"),
    ],
)
def test_the_duration_is_shown_as_minutes_and_seconds_under_an_hour_and_hours_from_there(
    seconds: int, shown: str
) -> None:
    # Setup
    info = a_link_info(duration_s=seconds)

    # Execute
    facts = info.facts()

    # Assert
    assert facts["duration"] == shown


@pytest.mark.parametrize(
    ("field", "name", "raw", "shown"),
    [
        ("title", "link_title", "Knife\x00skills\u200b101", "Knife skills 101"),
        ("uploader", "uploader", "Test\x1b[31m\u202eKitchen", "Test [31m Kitchen"),
    ],
)
def test_characters_that_cannot_be_printed_become_spaces(
    field: str, name: str, raw: str, shown: str
) -> None:
    # Setup
    info = a_link_info(**{field: raw})

    # Execute
    facts = info.facts()

    # Assert
    assert facts[name] == shown


@pytest.mark.parametrize("field", ["title", "uploader"])
def test_a_text_the_link_itself_let_through_too_long_is_clipped_to_the_details_value_limit(
    field: str,
) -> None:
    # Setup
    info = a_link_info()
    object.__setattr__(info, field, LONG_TEXT)

    # Execute
    facts = info.facts()

    # Assert
    assert max(len(text) for text in facts.values()) <= DETAIL_VALUE_LIMIT


def test_a_title_of_only_unprintable_characters_is_left_out() -> None:
    # Setup
    info = a_link_info(title="\x00\u200b\x00")

    # Execute
    facts = info.facts()

    # Assert
    assert "link_title" not in facts
