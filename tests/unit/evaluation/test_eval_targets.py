import pytest
from eval_builders import a_target, an_eval_targets

from stash.config import ProviderName, Thinking
from stash.evaluation import EvalTarget, EvalTargets, UnconfiguredProviderError

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
DEFAULT = Thinking.DEFAULT
OFF = Thinking.OFF


def choices(selected: tuple[EvalTarget, ...]) -> list[tuple[str, str]]:
    return [(target.choice.provider, target.choice.thinking) for target in selected]


def test_without_a_thinking_choice_the_configured_default_is_selected() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA, configured=DEFAULT).select(None, None)

    # Assert
    assert choices(selected) == [("ollama", "default")]


def test_without_a_thinking_choice_the_configured_off_is_selected() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA, configured=OFF).select(None, None)

    # Assert
    assert choices(selected) == [("ollama", "off")]


def test_a_thinking_choice_overrides_the_configured_value() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA, configured=OFF).select(None, (DEFAULT,))

    # Assert
    assert choices(selected) == [("ollama", "default")]


def test_thinking_values_are_selected_in_the_order_given() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA).select(None, (OFF, DEFAULT))

    # Assert
    assert choices(selected) == [("ollama", "off"), ("ollama", "default")]


def test_a_thinking_value_named_twice_is_selected_once() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA).select(None, (OFF, OFF))

    # Assert
    assert choices(selected) == [("ollama", "off")]


def test_providers_are_selected_in_the_order_given() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA, OPENROUTER).select(("openrouter", "ollama"), None)

    # Assert
    assert choices(selected) == [("openrouter", "default"), ("ollama", "default")]


def test_a_provider_named_twice_is_selected_once() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA, OPENROUTER).select(("ollama", "ollama"), None)

    # Assert
    assert choices(selected) == [("ollama", "default")]


def test_without_a_provider_choice_every_present_provider_is_selected_in_provider_order() -> None:
    # Execute
    selected = an_eval_targets(OPENROUTER, OLLAMA).select(None, None)

    # Assert
    assert choices(selected) == [("ollama", "default"), ("openrouter", "default")]


def test_without_a_provider_choice_only_the_present_providers_are_selected() -> None:
    # Execute
    selected = an_eval_targets(OPENROUTER).select(None, None)

    # Assert
    assert choices(selected) == [("openrouter", "default")]


def test_each_provider_runs_all_its_thinking_values_before_the_next_provider() -> None:
    # Execute
    selected = an_eval_targets(OLLAMA, OPENROUTER).select(("ollama", "openrouter"), (DEFAULT, OFF))

    # Assert
    assert choices(selected) == [
        ("ollama", "default"),
        ("ollama", "off"),
        ("openrouter", "default"),
        ("openrouter", "off"),
    ]


def test_selecting_a_provider_that_is_not_configured_names_it() -> None:
    # Execute
    with pytest.raises(UnconfiguredProviderError) as error:
        an_eval_targets(OLLAMA).select(("ollama", "groq"), None)

    # Assert
    assert str(error.value) == "provider groq is not configured"


def test_selecting_a_known_provider_that_has_no_target_says_it_is_not_configured() -> None:
    # Execute
    with pytest.raises(UnconfiguredProviderError) as error:
        an_eval_targets(OLLAMA).select(("openrouter",), None)

    # Assert
    assert str(error.value) == "provider openrouter is not configured"


def test_a_present_provider_missing_a_thinking_value_is_an_error_not_a_skip() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="ollama thinking=off"):
        EvalTargets((a_target(OLLAMA, DEFAULT),), DEFAULT)


def test_two_targets_for_the_same_choice_are_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="ollama thinking=default"):
        EvalTargets((a_target(OLLAMA, DEFAULT), a_target(OLLAMA, DEFAULT)), DEFAULT)
