from architecture_guard import method_callers_outside, project_sources

CREATE_OR_REPLACE = "save_item"
FILING = ("stash.store", "stash.capture.pipeline")


def test_a_create_or_replace_call_outside_the_allowed_modules_is_reported() -> None:
    # Setup
    sources = {"stash.lifecycle.x": "def f(store):\n    store.save_item(item)"}

    # Execute
    callers = method_callers_outside(CREATE_OR_REPLACE, FILING, sources)

    # Assert
    assert callers == ["stash.lifecycle.x"]


def test_a_create_or_replace_call_in_the_capture_pipeline_is_not_reported() -> None:
    # Setup
    sources = {"stash.capture.pipeline": "def f(self):\n    self._store.save_item(item)"}

    # Execute
    callers = method_callers_outside(CREATE_OR_REPLACE, FILING, sources)

    # Assert
    assert callers == []


def test_a_create_or_replace_call_in_another_capture_module_is_reported() -> None:
    # Setup
    sources = {"stash.capture.fixes": "def f(self):\n    self._store.save_item(item)"}

    # Execute
    callers = method_callers_outside(CREATE_OR_REPLACE, FILING, sources)

    # Assert
    assert callers == ["stash.capture.fixes"]


def test_a_conditional_update_call_is_not_reported() -> None:
    # Setup
    sources = {"stash.lifecycle.x": "def f(store):\n    store.update_item(item, replacing=read)"}

    # Execute
    callers = method_callers_outside(CREATE_OR_REPLACE, FILING, sources)

    # Assert
    assert callers == []


def test_only_the_store_and_the_capture_pipeline_create_or_replace_items() -> None:
    # Execute
    callers = method_callers_outside(CREATE_OR_REPLACE, FILING, project_sources())

    # Assert
    assert callers == []
