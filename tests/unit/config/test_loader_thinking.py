from pathlib import Path

from config_toml import OLLAMA_TABLE, a_toml, load, load_message, with_key

from stash.config import LlmTask, Thinking

EXAMPLE_FILE = Path(__file__).resolve().parents[3] / "deploy" / "stash.toml.example"


def with_thinking(entries: str) -> str:
    return a_toml(tables=f"{OLLAMA_TABLE}[llm.thinking]\n{entries}\n")


def test_without_a_thinking_table_every_task_is_default(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert {config.llm.thinking_for(task) for task in LlmTask} == {Thinking.DEFAULT}


def test_an_empty_thinking_table_leaves_every_task_default(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_thinking(""))

    # Assert
    assert {config.llm.thinking_for(task) for task in LlmTask} == {Thinking.DEFAULT}


def test_filing_off_turns_thinking_off_for_filing(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_thinking('filing = "off"'))

    # Assert
    assert config.llm.thinking_for(LlmTask.FILING) is Thinking.OFF


def test_filing_off_leaves_the_other_tasks_default(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_thinking('filing = "off"'))

    # Assert
    assert {
        config.llm.thinking_for(LlmTask.SUGGESTIONS),
        config.llm.thinking_for(LlmTask.VISION),
    } == {Thinking.DEFAULT}


def test_each_task_can_be_set_to_default_explicitly(tmp_path: Path) -> None:
    # Execute
    config = load(
        tmp_path,
        with_thinking('filing = "default"\nsuggestions = "default"\nvision = "default"'),
    )

    # Assert
    assert dict(config.llm.thinking) == {task: Thinking.DEFAULT for task in LlmTask}


def test_vision_and_suggestions_can_be_set_off(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_thinking('suggestions = "off"\nvision = "off"'))

    # Assert
    assert dict(config.llm.thinking) == {
        LlmTask.SUGGESTIONS: Thinking.OFF,
        LlmTask.VISION: Thinking.OFF,
    }


def test_a_value_other_than_default_or_off_names_the_key_and_the_choices(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, with_thinking('filing = "maybe"'))

    # Assert
    assert message == "llm.thinking.filing must be one of default, off"


def test_a_value_that_is_not_a_string_names_the_key(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, with_thinking("filing = 1"))

    # Assert
    assert message == "llm.thinking.filing must be a string"


def test_a_key_that_is_not_a_task_is_an_unknown_key(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, with_thinking('chat = "off"'))

    # Assert
    assert message == "unknown config key(s): llm.thinking.chat"


def test_the_example_file_turns_thinking_off_for_filing(tmp_path: Path) -> None:
    # Setup
    example = EXAMPLE_FILE.read_text(encoding="utf-8")

    # Execute
    config = load(tmp_path, example, with_key())

    # Assert
    assert config.llm.thinking_for(LlmTask.FILING) is Thinking.OFF
