import datetime as dt

import pytest

from stash.config import ConfigError
from stash.config._section import Section


def test_a_taken_key_is_not_reported_as_unknown_by_finish() -> None:
    # Setup
    section = Section("llm", {"model": "m"})
    section.take_text("model", "d")

    # Execute / Assert
    section.finish()


def test_an_untaken_key_is_reported_by_finish_with_its_path() -> None:
    # Setup
    section = Section("llm", {"modle": "m"})

    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.modle"):
        section.finish()


def test_take_text_returns_the_default_when_the_key_is_absent() -> None:
    # Execute
    value = Section("", {}).take_text("name", "fallback")

    # Assert
    assert value == "fallback"


def test_take_optional_text_returns_none_when_the_key_is_absent() -> None:
    # Execute
    value = Section("", {}).take_optional_text("name")

    # Assert
    assert value is None


def test_take_required_text_names_the_path_when_the_key_is_absent() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.model is required"):
        Section("llm", {}).take_required_text("model")


def test_take_integer_rejects_a_boolean() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"gpu\.n must be an integer"):
        Section("gpu", {"n": True}).take_integer("n", 1)


def test_take_number_returns_an_integer_as_a_float() -> None:
    # Execute
    value = Section("", {"n": 3}).take_number("n", 1.0)

    # Assert
    assert isinstance(value, float)


def test_take_table_returns_a_section_whose_path_includes_the_parent() -> None:
    # Setup
    table = Section("llm", {"ollama": {"x": 1}}).take_table("ollama")

    # Execute / Assert
    assert table is not None
    with pytest.raises(ConfigError, match=r"llm\.ollama\.x"):
        table.finish()


def test_take_table_or_empty_returns_an_empty_section_when_absent() -> None:
    # Execute / Assert
    Section("", {}).take_table_or_empty("llm").finish()


def test_take_optional_choice_returns_none_when_the_key_is_absent() -> None:
    # Execute
    value = Section("", {}).take_optional_choice("provider", ("a", "b"))

    # Assert
    assert value is None


def test_take_choice_returns_the_default_when_the_key_is_absent() -> None:
    # Execute
    value = Section("", {}).take_choice("busy_fallback", ("wait", "other"), "wait")

    # Assert
    assert value == "wait"


def test_take_required_choice_names_the_allowed_values_when_the_value_is_unknown() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="must be one of a, b"):
        Section("llm", {"provider": "c"}).take_required_choice("provider", ("a", "b"))


BAD_TIMES = [
    pytest.param("25:00", id="hour-25"),
    pytest.param("24:00", id="hour-24"),
    pytest.param("10:60", id="minute-60"),
    pytest.param("10:00:30", id="with-seconds"),
    pytest.param("9:00", id="one-digit-hour"),
    pytest.param("10:5", id="one-digit-minute"),
    pytest.param("1000", id="no-colon"),
    pytest.param("10.00", id="dot-separator"),
    pytest.param(" 10:00", id="leading-space"),
    pytest.param("10:00 ", id="trailing-space"),
    pytest.param("10:00\n", id="trailing-newline"),
    pytest.param("", id="empty"),
    pytest.param("ab:cd", id="letters"),
    pytest.param("\uff11\uff10:\uff10\uff10", id="full-width-digits"),
    pytest.param(10, id="integer"),
    pytest.param(10.5, id="float"),
    pytest.param(True, id="boolean"),
    pytest.param(["10:00"], id="list"),
]


def test_take_time_returns_the_default_when_the_key_is_absent() -> None:
    # Execute
    value = Section("nudges", {}).take_time("digest_time", dt.time(9, 0))

    # Assert
    assert value == dt.time(9, 0)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("07:05", dt.time(7, 5)),
        ("00:00", dt.time(0, 0)),
        ("23:59", dt.time(23, 59)),
    ],
)
def test_take_time_parses_a_two_digit_hour_and_minute(text: str, expected: dt.time) -> None:
    # Execute
    value = Section("nudges", {"digest_time": text}).take_time("digest_time", dt.time(9, 0))

    # Assert
    assert value == expected


@pytest.mark.parametrize("bad", BAD_TIMES)
def test_take_time_names_the_key_path_and_the_expected_format_for_a_bad_value(bad: object) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r'nudges\.digest_time.*"HH:MM"'):
        Section("nudges", {"digest_time": bad}).take_time("digest_time", dt.time(9, 0))


def test_take_time_rejects_a_native_toml_time_value() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r'nudges\.digest_time.*"HH:MM"'):
        Section("nudges", {"digest_time": dt.time(10, 0)}).take_time("digest_time", dt.time(9, 0))


def test_a_key_taken_by_take_time_is_not_reported_as_unknown_by_finish() -> None:
    # Setup
    section = Section("nudges", {"digest_time": "07:05"})
    section.take_time("digest_time", dt.time(9, 0))

    # Execute / Assert
    section.finish()
