from builders import a_capture
from capture_builders import an_agent_capture
from fakes.store_factories import StoreFactory, all_stores


@all_stores
def test_a_pending_agent_capture_reads_back_equal_to_the_one_added(
    open_store: StoreFactory,
) -> None:
    # Setup
    capture = an_agent_capture()
    with open_store() as store:
        store.add_capture(capture)

        # Execute
        [pending] = store.pending_captures()

        # Assert
        assert pending == capture


@all_stores
def test_an_agent_capture_fetched_by_id_keeps_its_source(open_store: StoreFactory) -> None:
    # Setup
    capture = an_agent_capture()
    with open_store() as store:
        store.add_capture(capture)

        # Execute
        fetched = store.get_capture(capture.id)

        # Assert
        assert fetched is not None and fetched.source == capture.source


@all_stores
def test_a_pending_telegram_capture_is_not_an_agent_capture_when_read_back(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.add_capture(a_capture())

        # Execute
        [pending] = store.pending_captures()

        # Assert
        assert not pending.source.is_agent
