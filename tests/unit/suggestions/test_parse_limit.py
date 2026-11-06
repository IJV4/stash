from suggestion_builders import a_raw_pick

from stash.suggestions import parse_suggestions

ALLOWED = {"a", "b", "c", "d"}


def ids_of(raw_picks: list[object], limit: int) -> list[str]:
    return [s.item_id for s in parse_suggestions({"picks": raw_picks}, ALLOWED, limit)]


def test_only_the_first_picks_up_to_the_limit_are_kept() -> None:
    # Execute
    ids = ids_of([a_raw_pick(i) for i in "abcd"], 3)

    # Assert
    assert ids == ["a", "b", "c"]


def test_fewer_picks_than_the_limit_are_all_kept() -> None:
    # Execute
    ids = ids_of([a_raw_pick("a")], 3)

    # Assert
    assert ids == ["a"]


def test_dropped_picks_do_not_count_towards_the_limit() -> None:
    # Setup
    raw = [
        a_raw_pick("zzz"),
        a_raw_pick("a", None),
        a_raw_pick("a"),
        a_raw_pick("a"),
        a_raw_pick("b"),
    ]

    # Execute
    ids = ids_of(raw, 2)

    # Assert
    assert ids == ["a", "b"]


def test_a_limit_of_one_keeps_only_the_first_usable_pick() -> None:
    # Execute
    ids = ids_of([a_raw_pick("a"), a_raw_pick("b")], 1)

    # Assert
    assert ids == ["a"]
