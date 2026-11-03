import logging

from fakes.chat_model import FakeChatModel
from filing_rig import build_filer
from log_records import recording_logs

from stash.llm import LlmBadOutput

FILER_LOGGER = "stash.filing.filer"
MODEL_OUTPUT = "sk-secret-model-output {not json"


def logged_by_filing_after_bad_output() -> list[tuple[int, str]]:
    filer = build_filer(FakeChatModel(error=LlmBadOutput(MODEL_OUTPUT)))
    with recording_logs(FILER_LOGGER) as recorder:
        filer.file("Ramen in Shibuya", None)
    return recorder.entries()


def test_an_answer_that_is_not_usable_is_logged_at_warning_naming_only_the_error_class() -> None:
    # Execute / Assert
    assert logged_by_filing_after_bad_output() == [
        (logging.WARNING, "filing model gave unusable output: LlmBadOutput")
    ]


def test_the_models_unusable_text_is_never_logged() -> None:
    # Execute
    entries = logged_by_filing_after_bad_output()

    # Assert
    assert [message for _, message in entries if MODEL_OUTPUT in message] == []
