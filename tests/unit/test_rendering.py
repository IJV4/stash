from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from builders import a_capture, an_item, an_outcome
from people_builders import a_key_date, a_person

from stash.capture import DeferralReason, Deferred, Duplicate
from stash.domain import Item, ItemType, KeyDateKind, NextKeyDate, Outcome, PersonSummary, Stage
from stash.lifecycle import ItemHistory
from stash.rendering import (
    history_lines,
    library_line,
    listing_line,
    person_line,
    result_line,
)

LOS_ANGELES = ZoneInfo("America/Los_Angeles")
CONTROL_CHARACTERS = "\x1b[31m\x07"


def a_place(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "item_type": ItemType.PLACE,
        "title": "Ramen in Shibuya",
        "stage": Stage.WANT_TO,
    }
    return an_item(**{**fields, **overrides})


def test_a_listing_line_appends_the_date_when_the_item_has_one() -> None:
    # Execute
    line = listing_line(a_place(stage=Stage.PLANNED, date=date(2026, 12, 5)))

    # Assert
    assert line == "Places · Ramen in Shibuya · Planned · 2026-12-05"


def test_terminal_control_characters_in_a_title_never_reach_the_line() -> None:
    # Execute
    line = listing_line(a_place(title="Ramen\x1b[31m red\x07"))

    # Assert
    assert line == "Places · Ramen [31m red · Want to"


def test_a_deferred_text_line_never_carries_control_characters() -> None:
    # Execute
    line = result_line(Deferred(a_capture(text="Ramen\x1b[2J now"), DeferralReason.GPU_BUSY))

    # Assert
    assert line == "deferred (gpu_busy) — Ramen [2J now"


def test_a_deferred_line_names_an_unreachable_ai_as_the_reason() -> None:
    # Execute
    line = result_line(Deferred(a_capture(text="Ramen"), DeferralReason.AI_UNAVAILABLE))

    # Assert
    assert line == "deferred (ai_unavailable) — Ramen"


def test_a_duplicate_result_line_says_it_was_already_saved() -> None:
    # Execute
    line = result_line(Duplicate())

    # Assert
    assert line == "duplicate — already saved"


def a_book(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "item_type": ItemType.BOOK,
        "title": "Dune",
        "stage": Stage.DONE,
        "kept": True,
    }
    return an_item(**{**fields, **overrides})


def history_lines_of(
    item: Item, outcomes: tuple[Outcome, ...] = (), children: tuple[Item, ...] = ()
) -> list[str]:
    return history_lines(ItemHistory(item, outcomes, children))


def test_a_library_line_leaves_the_rating_out_when_there_is_no_outcome() -> None:
    # Execute
    line = library_line(a_book(), None)

    # Assert
    assert line == "📚 Books: Dune"


def test_a_library_line_leaves_the_rating_out_when_the_last_outcome_is_unrated() -> None:
    # Execute
    line = library_line(a_book(), an_outcome(rating=None))

    # Assert
    assert line == "📚 Books: Dune"


def test_a_library_line_collapses_whitespace_and_hides_control_characters_in_the_title() -> None:
    # Execute
    line = library_line(a_book(title=f"Dune{CONTROL_CHARACTERS}\n  Messiah"), None)

    # Assert
    assert line == "📚 Books: Dune [31m Messiah"


def test_a_history_starts_with_the_listing_line() -> None:
    # Execute
    lines = history_lines_of(a_book(kept=False))

    # Assert
    assert lines == ["Books · Dune · Done"]


def test_a_history_marks_an_item_that_is_in_the_library() -> None:
    # Execute
    [first] = history_lines_of(a_book())

    # Assert
    assert first == "Books · Dune · Done · 📚 in library"


def test_a_history_does_not_mark_a_kept_item_that_was_dropped() -> None:
    # Execute
    [first, _] = history_lines_of(a_book(stage=Stage.DROPPED, drop_reason="boring"))

    # Assert
    assert first == "Books · Dune · Dropped"


def test_a_history_gives_the_reason_a_dropped_item_was_dropped() -> None:
    # Execute
    lines = history_lines_of(a_book(kept=False, stage=Stage.DROPPED, drop_reason="too long"))

    # Assert
    assert lines[1:] == ["Dropped because: too long"]


def test_a_history_gives_the_link_the_item_came_from() -> None:
    # Execute
    lines = history_lines_of(a_book(kept=False, source_url="https://example.com/dune"))

    # Assert
    assert lines[1:] == ["Link: https://example.com/dune"]


def test_a_history_gives_one_line_per_detail_in_the_order_they_were_stored() -> None:
    # Execute
    lines = history_lines_of(a_book(kept=False, details={"uploader": "Frank", "duration": "9h"}))

    # Assert
    assert lines[1:] == ["uploader: Frank", "duration: 9h"]


def test_a_history_gives_the_completion_date_and_rating_of_an_outcome() -> None:
    # Execute
    lines = history_lines_of(
        a_book(kept=False),
        (an_outcome(completed_on=date(2026, 11, 2), rating=4, notes="", takeaways=()),),
    )

    # Assert
    assert lines[1:] == ["Done 2026-11-02 · ⭐4"]


def test_a_history_gives_the_completion_date_alone_for_an_unrated_outcome() -> None:
    # Execute
    lines = history_lines_of(
        a_book(kept=False),
        (an_outcome(completed_on=date(2026, 11, 2), rating=None, notes="", takeaways=()),),
    )

    # Assert
    assert lines[1:] == ["Done 2026-11-02"]


def test_a_history_indents_the_notes_and_bullets_each_takeaway_under_the_outcome() -> None:
    # Setup
    outcome = an_outcome(
        rating=None, notes="Loved it", takeaways=("Start small", "Fear is the mind-killer")
    )

    # Execute
    lines = history_lines_of(a_book(kept=False), (outcome,))

    # Assert
    assert lines[2:] == ["  Loved it", "  • Start small", "  • Fear is the mind-killer"]


def test_a_history_lists_outcomes_in_the_order_given() -> None:
    # Setup
    first = an_outcome(id="o1", completed_on=date(2026, 10, 1), notes="", takeaways=())
    second = an_outcome(id="o2", completed_on=date(2026, 11, 1), notes="", takeaways=())

    # Execute
    lines = history_lines_of(a_book(kept=False), (first, second))

    # Assert
    assert lines[1:] == ["Done 2026-10-01 · ⭐4", "Done 2026-11-01 · ⭐4"]


def test_a_history_puts_the_link_details_outcomes_and_group_in_that_order() -> None:
    # Setup
    item = a_book(kept=False, source_url="https://example.com/d", details={"uploader": "Frank"})
    outcome = an_outcome(notes="", takeaways=("Start small",))
    child = an_item(id="c1", title="Part two", item_type=ItemType.BOOK, stage=Stage.INBOX)

    # Execute
    lines = history_lines_of(item, (outcome,), (child,))

    # Assert
    assert lines[1:] == [
        "Link: https://example.com/d",
        "uploader: Frank",
        "Done 2026-11-02 · ⭐4",
        "  • Start small",
        "In this group:",
        "  Books · Part two · Inbox",
    ]


def test_a_history_collapses_multi_line_notes_to_one_line() -> None:
    # Execute
    lines = history_lines_of(
        a_book(kept=False), (an_outcome(rating=None, notes="Line one\n\nLine   two", takeaways=()),)
    )

    # Assert
    assert lines[2:] == ["  Line one Line two"]


@pytest.mark.parametrize(
    "item",
    [
        a_book(kept=False, title=f"Dune{CONTROL_CHARACTERS}"),
        a_book(kept=False, stage=Stage.DROPPED, drop_reason=f"dull{CONTROL_CHARACTERS}"),
        a_book(kept=False, details={f"key{CONTROL_CHARACTERS}": "value"}),
        a_book(kept=False, details={"key": f"value{CONTROL_CHARACTERS}"}),
    ],
    ids=["title", "drop-reason", "detail-key", "detail-value"],
)
def test_control_characters_in_an_items_text_never_reach_the_history(item: Item) -> None:
    # Execute
    lines = history_lines_of(item)

    # Assert
    assert not any(character in "\n".join(lines) for character in "\x1b\x07")


@pytest.mark.parametrize(
    "outcome",
    [
        an_outcome(notes=f"Loved{CONTROL_CHARACTERS}", takeaways=()),
        an_outcome(notes="", takeaways=(f"Start small{CONTROL_CHARACTERS}",)),
    ],
    ids=["notes", "takeaway"],
)
def test_control_characters_in_an_outcomes_text_never_reach_the_history(outcome: Outcome) -> None:
    # Execute
    lines = history_lines_of(a_book(kept=False), (outcome,))

    # Assert
    assert not any(character in "\n".join(lines) for character in "\x1b\x07")


def test_control_characters_in_a_childs_title_never_reach_the_history() -> None:
    # Setup
    child = an_item(id="c1", title=f"Part{CONTROL_CHARACTERS}two")

    # Execute
    lines = history_lines_of(a_book(kept=False), children=(child,))

    # Assert
    assert not any(character in "\n".join(lines) for character in "\x1b\x07")


def test_control_characters_in_a_link_never_reach_the_history_even_if_the_item_carries_them() -> (
    None
):
    # Setup
    item = a_book(kept=False, source_url="https://example.com/a")
    object.__setattr__(item, "source_url", f"https://example.com/a{CONTROL_CHARACTERS}")

    # Execute
    lines = history_lines_of(item)

    # Assert
    assert not any(character in "\n".join(lines) for character in "\x1b\x07")


def a_summary(relation: str = "wife", **key_date: Any) -> PersonSummary:
    person = a_person(name="Ana", relation=relation, aliases=())
    fields: dict[str, Any] = {"month": 3, "day": 6, "year": 1993, "person_id": person.id}
    return PersonSummary(
        person, NextKeyDate(a_key_date(**{**fields, **key_date}), date(2027, 3, 6))
    )


def test_a_person_line_drops_control_characters_from_the_name() -> None:
    # Execute
    line = person_line(PersonSummary(a_person(name=f"Ana{CONTROL_CHARACTERS}", relation=""), None))

    # Assert
    assert line == "Ana [31m"


def test_a_person_line_drops_control_characters_from_the_relation() -> None:
    # Execute
    line = person_line(a_summary(relation=f"wife{CONTROL_CHARACTERS}"))

    # Assert
    assert line == "Ana (wife [31m) — birthday Sat Mar 6"


def test_a_person_line_drops_control_characters_from_an_other_keys_label() -> None:
    # Execute
    line = person_line(a_summary(kind=KeyDateKind.OTHER, label=f"Name day{CONTROL_CHARACTERS}"))

    # Assert
    assert line == "Ana (wife) — Name day [31m Sat Mar 6"
