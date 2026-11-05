from typing import Any

import pytest
from tool_rig import (
    DONE_ITEM,
    DONE_ITEM_OUTCOME,
    PARENT_ITEM,
    WANT_TO_ITEM,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
    store_snapshot,
)

TOOLS = ["get", "complete", "annotate", "set_stage", "keep", "group", "library"]
NOT_OBJECTS = [None, "w1", ["w1"], 3]
TWENTY_ONE = [f"point {number}" for number in range(21)]
NOT_TEXT = [5, True, ["w1"]]
NOT_WIRE_SAFE = ["", "   ", "a:b", "two words", "é", "a\x00b", "a\x1bb"]
TOO_LONG = ["x" * 41, "x" * 5000]
BAD_BOOLEANS = ["true", 1, 0]
UNKNOWN_ITEM_TYPE = (
    "unknown item_type 'spaceship' (valid: place, recipe, purchase, learn, book, media, idea, "
    "plan, activity, gift, other)"
)
NOT_WIRE_SAFE_MESSAGE = "must be non-blank, printable ASCII, without whitespace or ':'"

COMPLETE = {"item_id": WANT_TO_ITEM}
ANNOTATE = {"outcome_id": DONE_ITEM_OUTCOME, "notes": "Better"}
SET_STAGE = {"item_id": WANT_TO_ITEM, "stage": "doing"}
KEEP = {"item_id": DONE_ITEM, "kept": True}
GROUP = {"child_id": WANT_TO_ITEM, "parent_id": PARENT_ITEM}

Row = tuple[str, dict[str, Any], str]


def refusing(
    tool: str, base: dict[str, Any], name: str, values: list[Any], message: str
) -> list[Row]:
    return [(tool, {**base, name: value}, message) for value in values]


def bad_ids(tool: str, base: dict[str, Any], name: str, *, nullable: bool = False) -> list[Row]:
    not_text = NOT_TEXT if nullable else [*NOT_TEXT, None]
    return [
        *refusing(tool, base, name, not_text, f"{name} must be text"),
        *refusing(tool, base, name, NOT_WIRE_SAFE, f"{name} {NOT_WIRE_SAFE_MESSAGE}"),
        *refusing(tool, base, name, TOO_LONG, f"{name} must be at most 40 characters"),
    ]


REFUSED_CALLS: list[Row] = [
    *bad_ids("get", {}, "item_id"),
    ("get", {}, "item_id must be text"),
    ("get", {"item_id": "zz"}, "no item 'zz'"),
    *bad_ids("complete", COMPLETE, "item_id"),
    ("complete", {"item_id": "zz"}, "no item 'zz'"),
    *refusing("complete", COMPLETE, "rating", [True, False, 4.0, "4"], "rating must be an integer"),
    *refusing("complete", COMPLETE, "rating", [0, 6, -1], "rating must be between 1 and 5"),
    *refusing("complete", COMPLETE, "keep", BAD_BOOLEANS, "keep must be true or false"),
    *refusing("complete", COMPLETE, "notes", NOT_TEXT, "notes must be text"),
    *refusing("complete", COMPLETE, "notes", ["x" * 4001], "notes must be at most 4000 characters"),
    *refusing(
        "complete",
        COMPLETE,
        "takeaways",
        ["Start small", 5, ["a", 5]],
        "takeaways must be a list of text",
    ),
    *refusing(
        "complete", COMPLETE, "takeaways", [TWENTY_ONE], "takeaways must have at most 20 entries"
    ),
    *refusing(
        "complete", COMPLETE, "takeaways", [["x" * 501]], "takeaway must be at most 500 characters"
    ),
    *refusing("complete", COMPLETE, "completed_on", [20261105], "completed_on must be text"),
    *refusing(
        "complete",
        COMPLETE,
        "completed_on",
        ["yesterday", "2026-13-01"],
        "completed_on must be a date like 2026-11-05",
    ),
    *bad_ids("annotate", ANNOTATE, "outcome_id"),
    ("annotate", {**ANNOTATE, "outcome_id": "zz"}, "no outcome 'zz'"),
    *refusing("annotate", ANNOTATE, "notes", [None, 5, ["a"]], "notes must be text"),
    *refusing("annotate", ANNOTATE, "notes", ["x" * 4001], "notes must be at most 4000 characters"),
    *refusing(
        "annotate",
        ANNOTATE,
        "takeaways",
        ["Start small", ["a", 5]],
        "takeaways must be a list of text",
    ),
    *refusing(
        "annotate", ANNOTATE, "takeaways", [TWENTY_ONE], "takeaways must have at most 20 entries"
    ),
    *refusing(
        "annotate", ANNOTATE, "takeaways", [["x" * 501]], "takeaway must be at most 500 characters"
    ),
    ("annotate", {"outcome_id": DONE_ITEM_OUTCOME}, "notes must be text"),
    *bad_ids("set_stage", SET_STAGE, "item_id"),
    ("set_stage", {**SET_STAGE, "item_id": "zz"}, "no item 'zz'"),
    *refusing(
        "set_stage",
        SET_STAGE,
        "stage",
        ["soonish"],
        "unknown stage 'soonish' (valid: inbox, want_to, planned, doing, done, dropped)",
    ),
    *refusing("set_stage", SET_STAGE, "stage", ["done"], "done is reached by completing an item"),
    *refusing("set_stage", SET_STAGE, "stage", [None, 5], "stage must be text"),
    *refusing("set_stage", SET_STAGE, "reason", NOT_TEXT, "reason must be text"),
    *refusing(
        "set_stage",
        {**SET_STAGE, "stage": "dropped"},
        "reason",
        [5, ["a"], True],
        "reason must be text",
    ),
    *refusing(
        "set_stage", SET_STAGE, "reason", ["because"], "a reason is only for dropping an item"
    ),
    *refusing(
        "set_stage",
        {**SET_STAGE, "stage": "dropped"},
        "reason",
        ["x" * 301],
        "drop_reason must be at most 300 characters",
    ),
    ("set_stage", {"item_id": WANT_TO_ITEM, "stage": "planned"}, "planned items need a date"),
    *bad_ids("keep", KEEP, "item_id"),
    ("keep", {**KEEP, "item_id": "zz"}, "no item 'zz'"),
    *refusing("keep", KEEP, "kept", [*BAD_BOOLEANS, None], "kept must be true or false"),
    ("keep", {"item_id": WANT_TO_ITEM, "kept": True}, "only done items can be kept"),
    *bad_ids("group", GROUP, "child_id"),
    ("group", {**GROUP, "child_id": "zz"}, "no item 'zz'"),
    *bad_ids("group", GROUP, "parent_id", nullable=True),
    ("group", {**GROUP, "parent_id": "zz"}, "no item 'zz'"),
    ("group", {"child_id": WANT_TO_ITEM}, "parent_id is required (an id, or null)"),
    (
        "group",
        {"child_id": WANT_TO_ITEM, "parent_id": WANT_TO_ITEM},
        "groups are one level deep: an item cannot be its own parent",
    ),
    *refusing("library", {}, "item_type", [5, ["book"]], "item_type must be text"),
    *refusing("library", {}, "item_type", ["spaceship"], UNKNOWN_ITEM_TYPE),
    *refusing("library", {}, "limit", ["5", 5.0, True], "limit must be an integer"),
    *refusing("library", {}, "limit", [0, 51, -1], "limit must be between 1 and 50"),
]


def refused(tool: str, arguments: Any) -> tuple[dict[str, Any], bool]:
    store = a_tool_store()
    before = store_snapshot(store)
    answer = answer_of(getattr(lifecycle_tools_over(store), tool)(arguments))
    return answer, store_snapshot(store) == before


@pytest.mark.parametrize("tool", TOOLS)
@pytest.mark.parametrize("arguments", NOT_OBJECTS)
def test_arguments_that_are_not_an_object_are_refused_and_change_nothing(
    tool: str, arguments: Any
) -> None:
    # Execute
    outcome = refused(tool, arguments)

    # Assert
    assert outcome == ({"error": "arguments must be an object"}, True)


@pytest.mark.parametrize(("tool", "arguments", "message"), REFUSED_CALLS)
def test_a_call_with_bad_arguments_answers_the_refusal_and_changes_nothing(
    tool: str, arguments: dict[str, Any], message: str
) -> None:
    # Execute
    outcome = refused(tool, arguments)

    # Assert
    assert outcome == ({"error": message}, True)
