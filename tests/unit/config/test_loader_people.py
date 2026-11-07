from pathlib import Path

import pytest
from config_toml import a_toml, load, load_message, with_key

from stash.config import MAX_NUDGE_DAYS, PeopleConfig
from stash.config.loader import load_config

EXAMPLE_FILE = Path(__file__).resolve().parents[3] / "deploy" / "stash.toml.example"
PEOPLE_BLOCK_LINES = ["# [people]", "# lead_days = [14, 2, 0]"]


def with_people(body: str) -> str:
    return a_toml(top=f"[people]\n{body}\n")


def test_without_a_people_table_reminders_go_out_fourteen_and_two_days_before_and_on_the_day(
    tmp_path: Path,
) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.people.lead_days == (14, 2, 0)


def test_lead_days_are_read_in_the_order_written(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, with_people("lead_days = [30, 7, 0]"))

    # Assert
    assert config.people == PeopleConfig(lead_days=(30, 7, 0))


@pytest.mark.parametrize(
    ("literal", "message"),
    [
        pytest.param("[]", "at least one", id="empty"),
        pytest.param("[-1]", "between 0 and", id="negative"),
        pytest.param(f"[{MAX_NUDGE_DAYS + 1}]", "between 0 and", id="too-far"),
        pytest.param("[2, 2]", "repeat", id="repeated"),
        pytest.param("14", "a list of integers", id="not-a-list"),
        pytest.param("[1.5]", "a list of integers", id="float"),
        pytest.param("[true]", "a list of integers", id="boolean"),
    ],
)
def test_lead_days_that_are_empty_out_of_range_repeated_or_not_integers_are_refused(
    tmp_path: Path, literal: str, message: str
) -> None:
    # Execute
    refusal = load_message(tmp_path, with_people(f"lead_days = {literal}"))

    # Assert
    assert message in refusal


def test_an_unknown_key_in_the_people_table_is_refused(tmp_path: Path) -> None:
    # Execute
    refusal = load_message(tmp_path, with_people("lead_day = [1]"))

    # Assert
    assert "people.lead_day" in refusal


def test_the_example_file_loads_with_the_default_people_settings() -> None:
    # Execute
    config = load_config(EXAMPLE_FILE, with_key())

    # Assert
    assert config.people == PeopleConfig()


def test_the_example_files_people_block_works_once_uncommented(tmp_path: Path) -> None:
    # Setup
    lines = EXAMPLE_FILE.read_text(encoding="utf-8").splitlines()
    first = lines.index(PEOPLE_BLOCK_LINES[0])
    assert lines[first : first + len(PEOPLE_BLOCK_LINES)] == PEOPLE_BLOCK_LINES
    lines[first : first + len(PEOPLE_BLOCK_LINES)] = [
        line.removeprefix("# ") for line in PEOPLE_BLOCK_LINES
    ]

    # Execute
    config = load(tmp_path, "\n".join(lines), with_key())

    # Assert
    assert config.people == PeopleConfig()
