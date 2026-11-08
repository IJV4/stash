from architecture_guard import method_callers_outside, project_sources

UNGUARDED_DELETE = "delete_item"
STORE = ("stash.store",)


def test_no_module_outside_the_store_calls_the_unguarded_item_delete() -> None:
    # Execute
    callers = method_callers_outside(UNGUARDED_DELETE, STORE, project_sources())

    # Assert
    assert callers == []
