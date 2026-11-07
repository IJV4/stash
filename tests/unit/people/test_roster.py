from datetime import date

from people_builders import a_directory

from stash.domain import KeyDateKind, NextKeyDate

TODAY = date(2027, 3, 7)


def test_a_birthday_that_was_yesterday_is_listed_for_next_year() -> None:
    # Setup
    directory = a_directory()
    ana = directory.add("Ana")
    birthday = directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 6)

    # Execute
    [summary] = directory.roster(TODAY)

    # Assert
    assert summary.next_date == NextKeyDate(birthday, date(2028, 3, 6))


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


def test_people_without_key_dates_come_after_those_with_one_by_name() -> None:
    # Setup
    directory = a_directory()
    directory.add("Zed")
    directory.add("Bo")
    cy = directory.add("Cy")
    directory.add_key_date(cy.id, KeyDateKind.BIRTHDAY, 12, 1)

    # Execute
    names = [summary.person.name for summary in directory.roster(TODAY)]

    # Assert
    assert names == ["Cy", "Bo", "Zed"]


def test_a_window_keeps_only_the_people_whose_next_key_date_falls_inside_it() -> None:
    # Setup
    directory = a_directory()
    ana = directory.add("Ana")
    directory.add_key_date(ana.id, KeyDateKind.BIRTHDAY, 3, 17)
    bo = directory.add("Bo")
    directory.add_key_date(bo.id, KeyDateKind.BIRTHDAY, 3, 18)
    directory.add("Cy")

    # Execute
    names = [summary.person.name for summary in directory.roster(TODAY, within_days=10)]

    # Assert
    assert names == ["Ana"]
