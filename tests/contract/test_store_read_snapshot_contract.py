from fakes.store_factories import StoreFactory, all_stores

KEY = "library.theme"


@all_stores
def test_a_read_inside_a_snapshot_sees_what_was_stored_before_the_snapshot_began(
    open_store: StoreFactory,
) -> None:
    # Setup
    with open_store() as store:
        store.put_setting(KEY, "dark")

        # Execute
        with store.read_snapshot():
            value = store.get_setting(KEY)

        # Assert
        assert value == "dark"
