from planning_builders import a_raw_step

from stash.planning import MAX_PROPOSED_STEPS, parse_steps


def numbered(count: int) -> list[dict[str, object]]:
    return [a_raw_step(text=f"Step {n}", lead_days=n) for n in range(count)]


def test_the_cap_is_ten_steps() -> None:
    # Execute
    cap = MAX_PROPOSED_STEPS

    # Assert
    assert cap == 10


def test_fifty_valid_entries_yield_the_first_ten() -> None:
    # Execute
    steps = parse_steps({"steps": numbered(50)})

    # Assert
    assert [step.text for step in steps] == [f"Step {n}" for n in range(10)]


def test_exactly_ten_valid_entries_are_all_kept() -> None:
    # Execute
    steps = parse_steps({"steps": numbered(10)})

    # Assert
    assert len(steps) == 10


def test_invalid_entries_do_not_count_toward_the_cap() -> None:
    # Setup
    invalid = [a_raw_step(lead_days="soon") for _ in range(5)]

    # Execute
    steps = parse_steps({"steps": [*invalid, *numbered(12)]})

    # Assert
    assert [step.text for step in steps] == [f"Step {n}" for n in range(10)]
