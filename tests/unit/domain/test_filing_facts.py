from builders import a_filing

from stash.domain import MAX_DETAILS


def test_facts_are_added_to_the_details_the_model_wrote() -> None:
    # Setup
    filing = a_filing(details={"city": "Tokyo"})

    # Execute
    merged = filing.with_facts({"uploader": "Test Kitchen"})

    # Assert
    assert dict(merged.details) == {"city": "Tokyo", "uploader": "Test Kitchen"}


def test_a_fact_overrides_a_model_written_detail_with_the_same_key() -> None:
    # Setup
    filing = a_filing(details={"uploader": "someone else", "city": "Tokyo"})

    # Execute
    merged = filing.with_facts({"uploader": "Test Kitchen"})

    # Assert
    assert dict(merged.details) == {"uploader": "Test Kitchen", "city": "Tokyo"}


def test_no_facts_leave_the_details_as_they_were() -> None:
    # Setup
    filing = a_filing(details={"city": "Tokyo"})

    # Execute
    merged = filing.with_facts({})

    # Assert
    assert merged == filing


def test_facts_change_nothing_but_the_details() -> None:
    # Setup
    filing = a_filing(title="Knife skills", tags=("cooking",), people=("Ana",))

    # Execute
    merged = filing.with_facts({"uploader": "Test Kitchen"})

    # Assert
    assert (merged.title, merged.tags, merged.people) == ("Knife skills", ("cooking",), ("Ana",))


def test_the_filing_the_facts_were_added_to_keeps_its_own_details() -> None:
    # Setup
    filing = a_filing(details={"city": "Tokyo"})

    # Execute
    filing.with_facts({"uploader": "Test Kitchen"})

    # Assert
    assert dict(filing.details) == {"city": "Tokyo"}


def test_facts_added_to_a_full_set_of_details_are_kept_and_the_overflow_is_dropped() -> None:
    # Setup
    filing = a_filing(details={f"key{number}": "x" for number in range(MAX_DETAILS)})
    facts = {"link_title": "a", "uploader": "b", "duration": "1:00"}

    # Execute
    merged = filing.with_facts(facts)

    # Assert
    assert (len(merged.details), dict(merged.details).items() >= facts.items()) == (
        MAX_DETAILS,
        True,
    )


def test_making_room_for_facts_drops_the_last_details_the_model_wrote() -> None:
    # Setup
    filing = a_filing(details={f"key{number}": "x" for number in range(MAX_DETAILS)})

    # Execute
    merged = filing.with_facts({"uploader": "Test Kitchen"})

    # Assert
    assert "key0" in merged.details and f"key{MAX_DETAILS - 1}" not in merged.details


def test_a_fact_replacing_a_detail_needs_no_extra_room() -> None:
    # Setup
    details = {f"key{number}": "x" for number in range(MAX_DETAILS - 1)}
    filing = a_filing(details={"uploader": "someone else", **details})

    # Execute
    merged = filing.with_facts({"uploader": "Test Kitchen"})

    # Assert
    assert dict(merged.details) == {**details, "uploader": "Test Kitchen"}
