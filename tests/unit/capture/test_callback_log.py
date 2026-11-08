import logging
from collections.abc import Callable

from log_records import recording_logs

from stash.capture.callback_log import MAX_LOGGED_CALLBACK_CHARS, CallbackLog, Subject

LOGGER_NAME = "stash.capture.test_callback_log"
FORGED = "g" * 500
CLAMPED = FORGED[:MAX_LOGGED_CALLBACK_CHARS]


def logged_by(record: Callable[[CallbackLog], None]) -> list[tuple[int, str]]:
    with recording_logs(LOGGER_NAME) as recorder:
        record(CallbackLog(logging.getLogger(LOGGER_NAME)))
    return recorder.entries()


def test_an_invalid_value_is_a_warning_naming_the_subject_the_kind_and_the_value() -> None:
    # Execute
    entries = logged_by(lambda log: log.invalid(Subject.ITEM, "i1", "Stage", "limbo"))

    # Assert
    assert entries == [(logging.WARNING, "fix callback for item i1 has an invalid Stage 'limbo'")]


def test_an_invalid_value_that_is_missing_is_logged_as_none() -> None:
    # Execute
    entries = logged_by(lambda log: log.invalid(Subject.OUTCOME, "o1", "rating", None))

    # Assert
    assert entries == [(logging.WARNING, "fix callback for outcome o1 has an invalid rating None")]


def test_an_invalid_subject_id_is_cut_to_its_first_64_characters() -> None:
    # Execute
    entries = logged_by(lambda log: log.invalid(Subject.ITEM, FORGED, "Stage", "limbo"))

    # Assert
    assert entries == [
        (logging.WARNING, f"fix callback for item {CLAMPED} has an invalid Stage 'limbo'")
    ]


def test_an_invalid_value_is_cut_to_its_first_64_characters() -> None:
    # Execute
    entries = logged_by(lambda log: log.invalid(Subject.ITEM, "i1", "Stage", FORGED))

    # Assert
    assert entries == [
        (logging.WARNING, f"fix callback for item i1 has an invalid Stage {CLAMPED!r}")
    ]
