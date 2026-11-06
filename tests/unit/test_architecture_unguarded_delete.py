from architecture_guard import method_callers_outside, project_sources

UNGUARDED_DELETE = "delete_item"
STORE = ("stash.store",)


def test_a_call_to_the_method_outside_the_allowed_packages_is_reported() -> None:
    # Setup
    sources = {"stash.capture.x": "def f(store):\n    store.delete_item('i1')"}

    # Execute
    callers = method_callers_outside(UNGUARDED_DELETE, STORE, sources)

    # Assert
    assert callers == ["stash.capture.x"]


def test_a_call_inside_an_allowed_package_is_not_reported() -> None:
    # Setup
    sources = {"stash.store.sqlite": "def f(self):\n    self.delete_item('i1')"}

    # Execute
    callers = method_callers_outside(UNGUARDED_DELETE, STORE, sources)

    # Assert
    assert callers == []


def test_a_similarly_named_method_is_not_reported() -> None:
    # Setup
    sources = {"stash.capture.x": "def f(store):\n    store.delete_item_if_untouched('i1')"}

    # Execute
    callers = method_callers_outside(UNGUARDED_DELETE, STORE, sources)

    # Assert
    assert callers == []


def test_no_module_outside_the_store_calls_the_unguarded_item_delete() -> None:
    # Execute
    callers = method_callers_outside(UNGUARDED_DELETE, STORE, project_sources())

    # Assert
    assert callers == []
