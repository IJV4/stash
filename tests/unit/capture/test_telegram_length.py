import pytest

from stash.capture import telegram_length


@pytest.mark.parametrize(
    ("text", "units"),
    [("abc", 3), ("é…", 2), ("😀", 2), ("a😀b", 4)],
    ids=["ascii", "bmp-symbols", "one-emoji", "emoji-between-ascii"],
)
def test_telegram_length_counts_utf16_code_units(text: str, units: int) -> None:
    # Execute
    length = telegram_length(text)

    # Assert
    assert length == units
