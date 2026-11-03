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
