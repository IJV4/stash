from datetime import date

import pytest

from stash.store.backup import BackupName

NOVEMBER_SECOND = date(2026, 11, 2)
FULLWIDTH_DIGITS = "".join(chr(ord(digit) + 0xFEE0) for digit in "20261102")
FULLWIDTH_DIGITS_NAME = f"stash-{FULLWIDTH_DIGITS}.db"


def test_a_backup_is_named_after_its_day() -> None:
    # Execute
    name = BackupName.for_day(NOVEMBER_SECOND)

    # Assert
    assert str(name) == "stash-20261102.db"


def test_the_day_is_zero_padded() -> None:
    # Execute
    name = BackupName.for_day(date(2026, 1, 5))

    # Assert
    assert str(name) == "stash-20260105.db"


def test_a_file_name_made_by_for_day_parses_back_to_the_same_name() -> None:
    # Setup
    name = BackupName.for_day(NOVEMBER_SECOND)

    # Execute
    parsed = BackupName.parse(str(name))

    # Assert
    assert parsed == name


@pytest.mark.parametrize(
    "filename",
    [
        "stash.db",
        "stash-2026110.db",
        "stash-202611022.db",
        "stash-20261102.db.bak",
        "stash-20261102.sqlite",
        "stash-20261102.db\n",
        ".stash-20261102.db",
        "my-stash-20261102.db",
        "Stash-20261102.db",
        "stash-2026-11-02.db",
        FULLWIDTH_DIGITS_NAME,
        "stash-20261340.db",
        "stash-00000000.db",
        "notes.txt",
        "",
    ],
)
def test_a_file_name_that_only_looks_like_a_backup_is_not_a_backup_name(filename: str) -> None:
    # Execute
    parsed = BackupName.parse(filename)

    # Assert
    assert parsed is None


def test_a_later_day_sorts_after_an_earlier_one() -> None:
    # Setup
    earlier = BackupName.for_day(date(2026, 10, 31))
    later = BackupName.for_day(NOVEMBER_SECOND)

    # Assert
    assert earlier < later


def test_a_backup_name_cannot_be_modified() -> None:
    # Setup
    name = BackupName.for_day(NOVEMBER_SECOND)

    # Execute / Assert
    with pytest.raises(AttributeError):
        name.day = date(2026, 1, 1)  # type: ignore[misc]
