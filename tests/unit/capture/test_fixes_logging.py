import logging

import pytest
from builders import BASE
from capture_builders import store_with_filed_item
from log_records import recording_logs

from stash.capture import FixHandler

FIXES_LOGGER = "stash.capture.fixes"
WIRE_PREFIX_LENGTH = 64


def logged_by_applying(data: str) -> list[tuple[int, str]]:
    store, _ = store_with_filed_item()
    with recording_logs(FIXES_LOGGER) as recorder:
        FixHandler(store, lambda: BASE).apply(data)
    return recorder.entries()


@pytest.mark.parametrize("data", ["garbage", "stash:zz:c1", "stash:t:c1:extra", "stash:T:c1"])
def test_callback_data_that_does_not_parse_is_logged_at_warning(data: str) -> None:
    # Execute / Assert
    assert logged_by_applying(data) == [(logging.WARNING, f"unparseable fix callback: {data!r}")]


def test_unparseable_callback_data_is_logged_cut_to_its_first_64_characters() -> None:
    # Setup
    forged = "x" * 500

    # Execute / Assert
    assert logged_by_applying(forged) == [
        (logging.WARNING, f"unparseable fix callback: {forged[:WIRE_PREFIX_LENGTH]!r}")
    ]


@pytest.mark.parametrize("data", ["stash:t:ghost", "stash:s:ghost", "stash:T:ghost:recipe"])
def test_a_callback_for_an_unknown_item_is_logged_at_info(data: str) -> None:
    # Execute / Assert
    assert logged_by_applying(data) == [(logging.INFO, "fix callback for unknown item ghost")]


def test_a_question_callback_for_an_unknown_capture_is_logged_at_info() -> None:
    # Execute / Assert
    assert logged_by_applying("stash:q:ghost") == [
        (logging.INFO, "fix callback for unknown capture ghost")
    ]


def test_a_type_that_does_not_exist_is_logged_at_warning() -> None:
    # Execute / Assert
    assert logged_by_applying("stash:T:c1:spaceship") == [
        (logging.WARNING, "fix callback for item c1 has an invalid ItemType 'spaceship'")
    ]


def test_a_stage_that_does_not_exist_is_logged_at_warning() -> None:
    # Execute / Assert
    assert logged_by_applying("stash:S:c1:limbo") == [
        (logging.WARNING, "fix callback for item c1 has an invalid Stage 'limbo'")
    ]


def test_a_valid_fix_logs_nothing_at_warning_or_above() -> None:
    # Execute
    entries = logged_by_applying("stash:T:c1:recipe")

    # Assert
    assert [level for level, _ in entries if level >= logging.WARNING] == []


@pytest.mark.parametrize("kind", ["t", "s"])
def test_an_unknown_item_id_is_logged_cut_to_its_first_64_characters(kind: str) -> None:
    # Setup
    forged = "g" * 500

    # Execute / Assert
    assert logged_by_applying(f"stash:{kind}:{forged}") == [
        (logging.INFO, f"fix callback for unknown item {forged[:WIRE_PREFIX_LENGTH]}")
    ]


def test_an_unknown_capture_id_is_logged_cut_to_its_first_64_characters() -> None:
    # Setup
    forged = "g" * 500

    # Execute / Assert
    assert logged_by_applying(f"stash:q:{forged}") == [
        (logging.INFO, f"fix callback for unknown capture {forged[:WIRE_PREFIX_LENGTH]}")
    ]


def test_an_invalid_type_is_logged_cut_to_its_first_64_characters() -> None:
    # Setup
    forged = "x" * 500

    # Execute / Assert
    assert logged_by_applying(f"stash:T:c1:{forged}") == [
        (
            logging.WARNING,
            f"fix callback for item c1 has an invalid ItemType {forged[:WIRE_PREFIX_LENGTH]!r}",
        )
    ]


def test_an_invalid_stage_is_logged_cut_to_its_first_64_characters() -> None:
    # Setup
    forged = "x" * 500

    # Execute / Assert
    assert logged_by_applying(f"stash:S:c1:{forged}") == [
        (
            logging.WARNING,
            f"fix callback for item c1 has an invalid Stage {forged[:WIRE_PREFIX_LENGTH]!r}",
        )
    ]
