from contextlib import suppress

from builders import LATER, a_capture, a_source, an_item_at, an_outcome
from fakes.store_factories import StoreFactory, on_sqlite
from threads import run_concurrently, run_in_thread

from stash.domain import CaptureStatus, RawCapture, Stage
from stash.store import DuplicateOutcomeError, Store


def status_of(store: Store, capture: RawCapture) -> CaptureStatus | None:
    stored = store.get_capture(capture.id)
    return None if stored is None else stored.status


def item_stage(store: Store, item_id: str) -> Stage | None:
    item = store.get_item(item_id)
    return None if item is None else item.stage


@on_sqlite
def test_a_capture_added_on_the_main_thread_is_readable_from_another_thread(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        capture = a_capture()
        store.add_capture(capture)

        # Execute
        found = run_in_thread(lambda: store.get_capture(capture.id))

        # Assert
        assert found == capture


@on_sqlite
def test_a_capture_added_on_another_thread_is_readable_from_the_main_thread(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        capture = a_capture()
        run_in_thread(lambda: store.add_capture(capture))

        # Execute
        found = store.get_capture(capture.id)

        # Assert
        assert found == capture


@on_sqlite
def test_captures_added_concurrently_are_all_kept(open_store: StoreFactory) -> None:
    # Setup
    workers, captures_per_worker = 4, 15
    with open_store() as store:

        def add_captures(worker: int) -> None:
            for number in range(captures_per_worker):
                name = f"{worker}-{number}"
                store.add_capture(a_capture(id=f"c{name}", source=a_source(f"m{name}")))

        # Execute
        errors = run_concurrently(workers, add_captures)

        # Assert
        assert (errors, len(store.pending_captures())) == ([], workers * captures_per_worker)


@on_sqlite
def test_the_same_source_added_concurrently_is_accepted_exactly_once(
    open_store: StoreFactory,
) -> None:
    # Setup
    workers = 8
    outcomes: list[bool] = []
    with open_store() as store:

        def add_same_source(worker: int) -> None:
            outcomes.append(store.add_capture(a_capture(id=f"c{worker}")))

        # Execute
        errors = run_concurrently(workers, add_same_source)

        # Assert
        assert (errors, sorted(outcomes)) == ([], [False] * (workers - 1) + [True])


@on_sqlite
def test_completions_recorded_concurrently_are_all_kept(open_store: StoreFactory) -> None:
    # Setup
    workers = 8
    with open_store() as store:
        store.add_capture(a_capture())
        for worker in range(workers):
            store.save_item(an_item_at(Stage.DOING, id=f"i{worker}"))

        def complete(worker: int) -> None:
            item = an_item_at(Stage.DOING, id=f"i{worker}")
            outcome = an_outcome(id=f"o{worker}", item_id=item.id)
            store.record_completion(item.completed(LATER), outcome)

        # Execute
        errors = run_concurrently(workers, complete)

        # Assert
        finished = [
            (store.get_item(f"i{worker}"), len(store.outcomes_for(f"i{worker}")))
            for worker in range(workers)
        ]
        assert (errors, [(item and item.stage, count) for item, count in finished]) == (
            [],
            [(Stage.DONE, 1)] * workers,
        )


@on_sqlite
def test_a_capture_status_set_while_other_threads_write_leaves_every_effect(
    open_store: StoreFactory,
) -> None:
    # Setup
    count = 300
    requested = [
        a_capture(id=f"requested{n}", source=a_source(f"requested{n}")) for n in range(count)
    ]
    added = [a_capture(id=f"added{n}", source=a_source(f"added{n}")) for n in range(count)]
    refused = an_item_at(Stage.DOING, id="refused")
    taken = an_outcome(id="taken", item_id=refused.id)
    with open_store() as store:
        store.add_capture(a_capture())
        store.save_item(refused)
        store.add_outcome(taken)
        for capture in requested:
            store.add_capture(capture)
        for n in range(count):
            store.save_item(an_item_at(Stage.DOING, id=f"i{n}"))

        def request_captures() -> None:
            for capture in requested:
                store.set_capture_status(capture.id, CaptureStatus.REQUEST)

        def add_captures() -> None:
            for capture in added:
                store.add_capture(capture)

        def complete_items() -> None:
            for n in range(count):
                item = an_item_at(Stage.DOING, id=f"i{n}")
                outcome = an_outcome(id=f"o{n}", item_id=item.id)
                store.record_completion(item.completed(LATER), outcome)

        def refused_completions() -> None:
            for _ in range(count):
                with suppress(DuplicateOutcomeError):
                    store.record_completion(refused.completed(LATER), taken)

        writers = [request_captures, add_captures, complete_items, refused_completions]

        # Execute
        errors = run_concurrently(len(writers), lambda worker: writers[worker]())

        # Assert
        assert {
            "errors": errors,
            "requested": {status_of(store, capture) for capture in requested},
            "added": len(store.pending_captures()),
            "completed": {item_stage(store, f"i{n}") for n in range(count)},
        } == {
            "errors": [],
            "requested": {CaptureStatus.REQUEST},
            "added": count + 1,
            "completed": {Stage.DONE},
        }
