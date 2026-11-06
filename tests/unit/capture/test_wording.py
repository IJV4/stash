from datetime import date

from stash.capture.wording import counted, short_day


def test_a_day_reads_as_weekday_month_and_day_of_the_month_without_padding() -> None:
    # Execute
    text = short_day(date(2027, 2, 6))

    # Assert
    assert text == "Sat Feb 6"


def test_a_day_in_the_second_half_of_a_month_reads_with_both_digits() -> None:
    # Execute
    text = short_day(date(2027, 2, 13))

    # Assert
    assert text == "Sat Feb 13"


def test_one_of_something_is_counted_in_the_singular() -> None:
    # Execute
    text = counted(1, "step")

    # Assert
    assert text == "1 step"


def test_several_of_something_are_counted_in_the_plural() -> None:
    # Execute
    text = counted(3, "day")

    # Assert
    assert text == "3 days"


def test_none_of_something_is_counted_in_the_plural() -> None:
    # Execute
    text = counted(0, "step")

    # Assert
    assert text == "0 steps"
