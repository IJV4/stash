import pytest

from stash.filing.parse import parse_filing

FALLBACK = "Ramen in Shibuya"


def test_string_details_are_kept() -> None:
    # Assert
    assert parse_filing({"details": {"city": "Tokyo"}}, FALLBACK).details == {"city": "Tokyo"}


def test_details_that_are_not_text_are_dropped() -> None:
    # Assert
    assert parse_filing({"details": {"city": "Tokyo", "n": 3}}, FALLBACK).details == {
        "city": "Tokyo"
    }


def test_details_with_a_blank_key_or_value_are_dropped() -> None:
    # Execute
    filing = parse_filing({"details": {"city": "  ", " ": "Tokyo", "author": "Ana"}}, FALLBACK)

    # Assert
    assert filing.details == {"author": "Ana"}


def test_a_detail_key_is_clipped_to_50_characters() -> None:
    # Execute
    filing = parse_filing({"details": {"k" * 90: "v"}}, FALLBACK)

    # Assert
    assert list(filing.details) == ["k" * 50]


def test_a_huge_detail_value_is_clamped_to_300_characters() -> None:
    # Execute
    filing = parse_filing({"details": {"note": "v" * 5000}}, FALLBACK)

    # Assert
    assert filing.details == {"note": "v" * 300}


def test_detail_whitespace_is_collapsed() -> None:
    # Execute
    filing = parse_filing({"details": {" the  city ": "To\nkyo  "}}, FALLBACK)

    # Assert
    assert filing.details == {"the city": "To kyo"}


def test_at_most_20_details_are_kept_in_order() -> None:
    # Setup
    details = {f"key{number:02d}": "v" for number in range(30)}

    # Execute
    filing = parse_filing({"details": details}, FALLBACK)

    # Assert
    assert list(filing.details) == [f"key{number:02d}" for number in range(20)]


def test_dropped_details_do_not_count_towards_the_limit_of_20() -> None:
    # Setup
    details = {f"bad{number}": 1 for number in range(10)} | {f"ok{n:02d}": "v" for n in range(20)}

    # Execute
    filing = parse_filing({"details": details}, FALLBACK)

    # Assert
    assert len(filing.details) == 20


def test_tags_are_kept_in_order() -> None:
    # Assert
    assert parse_filing({"tags": ["ramen", "dinner"]}, FALLBACK).tags == ("ramen", "dinner")


def test_30_tags_are_cut_to_the_first_10() -> None:
    # Setup
    tags = [f"tag{number}" for number in range(30)]

    # Execute
    filing = parse_filing({"tags": tags}, FALLBACK)

    # Assert
    assert filing.tags == tuple(tags[:10])


def test_tags_that_are_not_text_or_are_blank_are_dropped() -> None:
    # Assert
    assert parse_filing({"tags": ["ramen", 3, None, "  ", ["x"], "dinner"]}, FALLBACK).tags == (
        "ramen",
        "dinner",
    )


def test_duplicate_tags_are_dropped_keeping_the_first() -> None:
    # Assert
    assert parse_filing({"tags": ["ramen", "dinner", "ramen", " ramen "]}, FALLBACK).tags == (
        "ramen",
        "dinner",
    )


def test_a_tag_is_clipped_to_40_characters() -> None:
    # Assert
    assert parse_filing({"tags": ["t" * 90]}, FALLBACK).tags == ("t" * 40,)


def test_dropped_tags_do_not_count_towards_the_limit_of_10() -> None:
    # Setup
    tags = [3] * 10 + [f"tag{number}" for number in range(10)]

    # Execute
    filing = parse_filing({"tags": tags}, FALLBACK)

    # Assert
    assert len(filing.tags) == 10


def test_people_are_kept_in_order() -> None:
    # Assert
    assert parse_filing({"people": ["Ana", "Ben"]}, FALLBACK).people == ("Ana", "Ben")


def test_10_people_are_cut_to_the_first_5() -> None:
    # Setup
    people = [f"Person {number}" for number in range(10)]

    # Execute
    filing = parse_filing({"people": people}, FALLBACK)

    # Assert
    assert filing.people == tuple(people[:5])


def test_a_person_is_clipped_to_80_characters() -> None:
    # Assert
    assert parse_filing({"people": ["p" * 200]}, FALLBACK).people == ("p" * 80,)


def test_duplicate_and_blank_people_are_dropped() -> None:
    # Assert
    assert parse_filing({"people": ["Ana", "", "Ana", 7, "Ben"]}, FALLBACK).people == (
        "Ana",
        "Ben",
    )


@pytest.mark.parametrize("field", ["tags", "people"])
def test_a_bare_string_where_a_list_is_expected_is_empty(field: str) -> None:
    # Execute
    filing = parse_filing({field: "ramen"}, FALLBACK)

    # Assert
    assert (filing.tags, filing.people) == ((), ())
