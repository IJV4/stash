from typing import Any

from builders import BASE, an_item, stored_completion
from fakes.memory_store import MemoryStore
from tool_rig import (
    DONE_ITEM,
    PARENT_ITEM,
    WANT_TO_ITEM,
    a_tool_store,
    answer_of,
    lifecycle_tools_over,
    store_snapshot,
)

from stash.domain import ItemType, Stage


def staged(arguments: dict[str, Any], store: MemoryStore | None = None) -> dict[str, Any]:
    tools = lifecycle_tools_over(store or a_tool_store())
    return answer_of(tools.set_stage({"item_id": WANT_TO_ITEM, **arguments}))


def test_set_stage_moves_the_item_to_the_stage() -> None:
    # Execute
    answer = staged({"stage": "doing"})

    # Assert
    assert answer["item"]["stage"] == "doing"


def test_set_stage_saves_the_move_in_the_store() -> None:
    # Setup
    store = a_tool_store()

    # Execute
    staged({"stage": "doing"}, store)

    # Assert
    assert store.get_item(WANT_TO_ITEM) == an_item(
        id="w1", title="Dune", item_type=ItemType.BOOK, stage=Stage.DOING, updated_at=BASE
    )


def test_set_stage_dropped_records_the_reason() -> None:
    # Execute
    answer = staged({"stage": "dropped", "reason": "lost interest"})

    # Assert
    assert (answer["item"]["stage"], answer["item"]["drop_reason"]) == ("dropped", "lost interest")


def test_set_stage_dropped_without_a_reason_drops_the_item_all_the_same() -> None:
    # Execute
    answer = staged({"stage": "dropped"})

    # Assert
    assert (answer["item"]["stage"], answer["item"]["drop_reason"]) == ("dropped", None)


def test_set_stage_done_answers_the_domains_refusal() -> None:
    # Execute
    answer = staged({"stage": "done"})

    # Assert
    assert answer == {"error": "done is reached by completing an item"}


def test_set_stage_done_leaves_the_store_as_it_was() -> None:
    # Setup
    store = a_tool_store()
    before = store_snapshot(store)

    # Execute
    staged({"stage": "done"}, store)

    # Assert
    assert store_snapshot(store) == before


def test_set_stage_with_a_reason_for_a_stage_other_than_dropped_answers_an_error() -> None:
    # Execute
    answer = staged({"stage": "doing", "reason": "because"})

    # Assert
    assert answer == {"error": "a reason is only for dropping an item"}


def test_set_stage_planned_for_an_item_without_a_date_answers_the_domains_refusal() -> None:
    # Execute
    answer = staged({"stage": "planned"})

    # Assert
    assert answer == {"error": "planned items need a date"}


def test_set_stage_with_an_unknown_stage_lists_the_valid_ones() -> None:
    # Execute
    answer = staged({"stage": "soonish"})

    # Assert
    assert answer["error"].startswith("unknown stage 'soonish' (valid: inbox, want_to")


def kept(arguments: dict[str, Any], item_id: str = DONE_ITEM) -> dict[str, Any]:
    tools = lifecycle_tools_over(a_tool_store())
    return answer_of(tools.keep({"item_id": item_id, **arguments}))


def test_keep_true_puts_a_done_item_in_the_library() -> None:
    # Execute
    answer = kept({"kept": True})

    # Assert
    assert (answer["item"]["kept"], answer["item"]["in_library"]) == (True, True)


def test_keep_false_takes_a_kept_item_out_of_the_library() -> None:
    # Setup
    store = MemoryStore()
    stored_completion(store, "k1", kept=True)

    # Execute
    answer = answer_of(lifecycle_tools_over(store).keep({"item_id": "k1", "kept": False}))

    # Assert
    assert answer["item"]["kept"] is False


def test_keeping_an_item_that_is_not_done_answers_the_domains_refusal() -> None:
    # Execute
    answer = kept({"kept": True}, item_id=WANT_TO_ITEM)

    # Assert
    assert answer == {"error": "only done items can be kept"}


def grouped(arguments: dict[str, Any], store: MemoryStore | None = None) -> dict[str, Any]:
    tools = lifecycle_tools_over(store or a_tool_store())
    return answer_of(tools.group({"child_id": WANT_TO_ITEM, **arguments}))


def test_group_puts_the_child_under_the_parent() -> None:
    # Execute
    answer = grouped({"parent_id": PARENT_ITEM})

    # Assert
    assert answer["item"]["parent_id"] == PARENT_ITEM


def test_group_saves_the_parent_in_the_store() -> None:
    # Setup
    store = a_tool_store()

    # Execute
    grouped({"parent_id": PARENT_ITEM}, store)

    # Assert
    assert store.children_of(PARENT_ITEM) == [store.get_item(WANT_TO_ITEM)]


def test_group_with_a_null_parent_takes_the_child_out_of_its_group() -> None:
    # Setup
    store = a_tool_store()
    grouped({"parent_id": PARENT_ITEM}, store)

    # Execute
    answer = grouped({"parent_id": None}, store)

    # Assert
    assert answer["item"]["parent_id"] is None


def test_group_with_a_null_parent_leaves_the_store_without_children_of_the_parent() -> None:
    # Setup
    store = a_tool_store()
    grouped({"parent_id": PARENT_ITEM}, store)

    # Execute
    grouped({"parent_id": None}, store)

    # Assert
    assert store.children_of(PARENT_ITEM) == []


def test_grouping_an_item_under_itself_answers_the_domains_refusal() -> None:
    # Execute
    answer = grouped({"parent_id": WANT_TO_ITEM})

    # Assert
    assert answer["error"].startswith("groups are one level deep")


def test_grouping_under_an_unknown_parent_answers_an_error_naming_it() -> None:
    # Execute
    answer = grouped({"parent_id": "zz"})

    # Assert
    assert answer == {"error": "no item 'zz'"}
