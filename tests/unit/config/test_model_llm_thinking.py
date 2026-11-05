import pytest
from config_builders import an_llm_config, both_providers

from stash.config import LlmTask, ModelChoice, ProviderName, Thinking

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
ALL_OFF = {task: Thinking.OFF for task in LlmTask}


def test_thinking_values_are_the_config_vocabulary() -> None:
    # Assert
    assert [thinking.value for thinking in Thinking] == ["default", "off"]


def test_a_task_without_a_thinking_setting_is_default() -> None:
    # Setup
    config = an_llm_config(thinking={LlmTask.FILING: Thinking.OFF})

    # Execute
    thinking = config.thinking_for(LlmTask.SUGGESTIONS)

    # Assert
    assert thinking is Thinking.DEFAULT


def test_a_task_with_a_thinking_setting_gets_it() -> None:
    # Setup
    config = an_llm_config(thinking={LlmTask.FILING: Thinking.OFF})

    # Execute
    thinking = config.thinking_for(LlmTask.FILING)

    # Assert
    assert thinking is Thinking.OFF


def test_a_config_without_a_thinking_table_has_default_thinking_for_every_task() -> None:
    # Setup
    config = an_llm_config()

    # Execute
    thinking = {task: config.thinking_for(task) for task in LlmTask}

    # Assert
    assert set(thinking.values()) == {Thinking.DEFAULT}


def test_the_thinking_settings_do_not_change_when_the_source_mapping_does() -> None:
    # Setup
    source = {LlmTask.FILING: Thinking.OFF}
    config = an_llm_config(thinking=source)

    # Execute
    source[LlmTask.FILING] = Thinking.DEFAULT

    # Assert
    assert config.thinking_for(LlmTask.FILING) is Thinking.OFF


def test_the_thinking_settings_cannot_be_modified() -> None:
    # Setup
    config = an_llm_config()

    # Execute / Assert
    with pytest.raises(TypeError):
        config.thinking[LlmTask.FILING] = Thinking.OFF


def test_a_choice_for_a_task_combines_its_provider_and_its_thinking() -> None:
    # Setup
    config = an_llm_config(
        providers=both_providers(),
        tasks={LlmTask.FILING: OPENROUTER},
        thinking={LlmTask.FILING: Thinking.OFF},
    )

    # Execute
    choice = config.choice_for(LlmTask.FILING)

    # Assert
    assert choice == ModelChoice(OPENROUTER, Thinking.OFF)


def test_a_choice_can_move_to_another_provider_keeping_its_thinking() -> None:
    # Execute
    moved = ModelChoice(OLLAMA, Thinking.OFF).with_provider(OPENROUTER)

    # Assert
    assert moved == ModelChoice(OPENROUTER, Thinking.OFF)


def test_a_choice_reads_as_its_provider_and_thinking() -> None:
    # Execute
    text = str(ModelChoice(OLLAMA, Thinking.OFF))

    # Assert
    assert text == "ollama thinking=off"


def test_without_thinking_settings_each_configured_provider_needs_only_the_default_model() -> None:
    # Setup
    config = an_llm_config(providers=both_providers())

    # Execute
    choices = config.model_choices()

    # Assert
    assert choices == {
        ModelChoice(OLLAMA, Thinking.DEFAULT),
        ModelChoice(OPENROUTER, Thinking.DEFAULT),
    }


def test_when_one_task_is_off_each_configured_provider_needs_both_models() -> None:
    # Setup
    config = an_llm_config(providers=both_providers(), thinking={LlmTask.FILING: Thinking.OFF})

    # Execute
    choices = config.model_choices()

    # Assert
    assert choices == {
        ModelChoice(provider, thinking)
        for provider in (OLLAMA, OPENROUTER)
        for thinking in Thinking
    }


def test_when_every_task_is_off_each_configured_provider_needs_only_the_off_model() -> None:
    # Setup
    config = an_llm_config(providers=both_providers(), thinking=ALL_OFF)

    # Execute
    choices = config.model_choices()

    # Assert
    assert choices == {ModelChoice(OLLAMA, Thinking.OFF), ModelChoice(OPENROUTER, Thinking.OFF)}


def test_only_configured_providers_have_model_choices() -> None:
    # Setup
    config = an_llm_config(thinking={LlmTask.FILING: Thinking.OFF})

    # Execute
    providers = {choice.provider for choice in config.model_choices()}

    # Assert
    assert providers == {OLLAMA}
