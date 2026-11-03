from builders import a_capture, a_source
from fakes.store_factories import StoreFactory, all_stores
from threads import run_concurrently, run_in_thread


@all_stores
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


@all_stores
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


@all_stores
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


@all_stores
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
