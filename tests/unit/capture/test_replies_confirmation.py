import pytest

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT
from stash.capture.replies import (
    DEFERRED_TEXT,
    TELEGRAM_TEXT_LIMIT,
    Button,
    Reply,
)


def test_a_button_with_a_blank_label_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="label"):
        Button("  ", "stash:t:i1")


def test_a_button_with_data_over_the_telegram_limit_in_bytes_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="64 bytes"):
        Button("Go", "é" * (TELEGRAM_CALLBACK_LIMIT // 2 + 1))


def test_a_reply_with_blank_text_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="text"):
        Reply(" \n", ())


def test_a_reply_over_the_telegram_text_limit_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="4096"):
        Reply("x" * (TELEGRAM_TEXT_LIMIT + 1), ())


def test_a_reply_over_the_telegram_text_limit_in_utf16_units_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="4096"):
        Reply("😀" * 2049, ())


def test_the_deferred_notices_cannot_be_changed_at_runtime() -> None:
    # Execute / Assert
    with pytest.raises(TypeError):
        DEFERRED_TEXT["gpu_busy"] = "changed"  # type: ignore[index]
