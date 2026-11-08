from datetime import UTC, datetime

from app_builders import an_app, stored
from builders import an_item, fetched_item

from stash.domain import Stage

LATE_EVENING_IN_LOS_ANGELES = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)


def test_the_apps_lifecycle_works_on_the_store_the_app_was_given() -> None:
    # Setup
    store = stored(an_item(id="a", capture_id="ca"))
    app = an_app(store=store)

    # Execute
    app.lifecycle.set_stage("a", Stage.DOING)

    # Assert
    assert fetched_item(store, "a").stage is Stage.DOING
