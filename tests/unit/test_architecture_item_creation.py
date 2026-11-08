from architecture_guard import method_callers_outside, project_sources

CREATE_OR_REPLACE = "save_item"
FILING = ("stash.store", "stash.capture.pipeline")


def test_only_the_store_and_the_capture_pipeline_create_or_replace_items() -> None:
    # Execute
    callers = method_callers_outside(CREATE_OR_REPLACE, FILING, project_sources())

    # Assert
    assert callers == []
