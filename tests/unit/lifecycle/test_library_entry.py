from builders import COMPLETED_ON, an_item, an_outcome

from stash.lifecycle import LibraryEntry


def test_an_entry_reports_the_rating_of_its_last_outcome() -> None:
    # Setup
    entry = LibraryEntry(an_item(), an_outcome(rating=4))

    # Execute
    rating = entry.rating

    # Assert
    assert rating == 4


def test_an_entry_whose_last_outcome_has_no_rating_has_no_rating() -> None:
    # Setup
    entry = LibraryEntry(an_item(), an_outcome(rating=None))

    # Execute
    rating = entry.rating

    # Assert
    assert rating is None


def test_an_entry_without_an_outcome_has_no_rating() -> None:
    # Setup
    entry = LibraryEntry(an_item(), None)

    # Execute
    rating = entry.rating

    # Assert
    assert rating is None


def test_an_entry_reports_the_completion_date_of_its_last_outcome() -> None:
    # Setup
    entry = LibraryEntry(an_item(), an_outcome())

    # Execute
    completed_on = entry.completed_on

    # Assert
    assert completed_on == COMPLETED_ON


def test_an_entry_without_an_outcome_has_no_completion_date() -> None:
    # Setup
    entry = LibraryEntry(an_item(), None)

    # Execute
    completed_on = entry.completed_on

    # Assert
    assert completed_on is None
