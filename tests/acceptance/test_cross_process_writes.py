import threading
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from builders import an_item, fetched_item, stored_item
from capture_rig import a_fix_handler
from fakes.chat_model import FakeChatModel
from fakes.store_factories import opened, two_connections
from lifecycle_rig import a_lifecycle
from planning_builders import steps_reply, stored_date_night
from planning_rig import a_planning
from threads import await_signal, start

from stash.capture.replies import busy
from stash.domain import ItemType, Stage
from stash.store._transaction import immediate_transaction

SHORT_WAIT = timedelta(milliseconds=50)
LONG_ENOUGH_TO_SEE_A_WAIT = 0.3


def test_a_second_process_waits_for_the_first_and_both_changes_survive(tmp_path: Path) -> None:
    # Setup
    with two_connections(tmp_path) as (first, second):
        stored_item(first, stage=Stage.DONE)
        read = threading.Event()
        kept = start(lambda: (await_signal(read), a_lifecycle(second).keep("i1", True)))

        # Execute
        with first.writing():
            item = fetched_item(first, "i1")
            read.set()
            kept.join(LONG_ENOUGH_TO_SEE_A_WAIT)
            first.update_item(replace(item, note="from first"))
        kept.join()

        # Assert
        final = fetched_item(first, "i1")
        assert (final.note, final.kept) == ("from first", True)


def test_a_writer_that_waits_longer_than_the_timeout_gets_the_busy_reply(tmp_path: Path) -> None:
    # Setup
    with two_connections(tmp_path, SHORT_WAIT) as (first, second):
        stored_item(first)

        # Execute
        with first.writing():
            reply = a_fix_handler(second).apply(f"stash:T:i1:{ItemType.BOOK.value}")

        # Assert
        assert reply == busy()
        assert fetched_item(first, "i1").item_type is ItemType.PLACE


def test_a_failure_inside_writing_rolls_back_every_write_in_it(tmp_path: Path) -> None:
    # Setup
    with opened(tmp_path / "stash.db") as store:
        stored_item(store)

        # Execute
        with pytest.raises(RuntimeError), store.writing():
            a_lifecycle(store).complete("i1", rating=4)
            raise RuntimeError

        # Assert
        assert fetched_item(store, "i1") == an_item()
        assert store.outcomes_for("i1") == []


def test_a_caught_failure_in_a_nested_write_keeps_the_writes_before_it(tmp_path: Path) -> None:
    # Setup
    with opened(tmp_path / "stash.db") as store:
        stored_item(store)
        connection = store._connection

        # Execute
        with store.writing():
            store.update_item(replace(an_item(), note="before"))
            with pytest.raises(RuntimeError), immediate_transaction(connection):
                store.update_item(replace(an_item(), note="inside"))
                raise RuntimeError

        # Assert
        assert fetched_item(store, "i1").note == "before"


def test_the_store_lock_is_not_held_while_the_model_is_asked(tmp_path: Path) -> None:
    # Setup
    with two_connections(tmp_path, SHORT_WAIT) as (first, second):
        stored_date_night(first)
        stored_item(first, id="other")

        class WritingModel(FakeChatModel):
            def complete_json(self, *args: object, **kwargs: object) -> dict[str, object]:
                second.update_item(replace(an_item(id="other"), note="written while asking"))
                return steps_reply(1)

        # Execute
        planning = a_planning(first, WritingModel())
        planning.propose_for("date-night")

        # Assert
        assert fetched_item(first, "other").note == "written while asking"
