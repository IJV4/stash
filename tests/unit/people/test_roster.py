from datetime import date

from people_builders import a_directory

from stash.domain import KeyDateKind, NextKeyDate

TODAY = date(2027, 3, 7)


def test_a_person_with_several_key_dates_is_listed_with_the_soonest() -> None:
    # Setup
    directory = a_directory()
    ana = directory.add("Ana")
    directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 6)
    anniversary = directory.add_key_date(ana.id, KeyDateKind.ANNIVERSARY, 6, 1)

    # Execute
    [summary] = directory.roster(TODAY)

    # Assert
    assert summary.next_date == NextKeyDate(anniversary, date(2027, 6, 1))
