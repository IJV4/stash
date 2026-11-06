from dataclasses import FrozenInstanceError
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import pytest
from app_builders import an_app, stored
from builders import an_item, fetched_item
from eval_builders import an_eval_targets
from fakes.close_counter import CloseCounter
from lifecycle_rig import a_lifecycle

from stash.capture.callbacks import FixAction, FixKind
from stash.config import Thinking
from stash.domain import Stage
from stash.evaluation import EvalTargets


def test_closing_the_app_closes_its_resources() -> None:
    # Setup
    resources = CloseCounter()
    app = an_app(resources=resources)

    # Execute
    app.close()

    # Assert
    assert resources.closes == 1


def test_the_app_cannot_be_modified() -> None:
    # Setup
    app = an_app()

    # Execute / Assert
    with pytest.raises(FrozenInstanceError):
        app.ocr = None  # type: ignore[misc, assignment]


def test_the_eval_targets_cannot_be_modified() -> None:
    # Setup
    app = an_app(eval_targets=an_eval_targets())

    # Execute / Assert
    with pytest.raises(FrozenInstanceError):
        app.eval_targets.configured = Thinking.OFF  # type: ignore[misc]


def test_the_eval_targets_do_not_change_when_the_source_mapping_does() -> None:
    # Setup
    source = list(an_eval_targets().targets)
    app = an_app(eval_targets=EvalTargets(source, Thinking.DEFAULT))

    # Execute
    source.clear()

    # Assert
    assert len(app.eval_targets.targets) == len(Thinking)


LATE_EVENING_IN_LOS_ANGELES = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)


def test_local_now_is_the_clock_in_the_configured_timezone() -> None:
    # Setup
    app = an_app(clock=lambda: LATE_EVENING_IN_LOS_ANGELES)

    # Execute
    now = app.local_now()

    # Assert
    assert (now, now.tzinfo) == (LATE_EVENING_IN_LOS_ANGELES, ZoneInfo("America/Los_Angeles"))


def test_today_is_the_calendar_day_in_the_configured_timezone() -> None:
    # Setup
    app = an_app(clock=lambda: LATE_EVENING_IN_LOS_ANGELES)

    # Execute
    today = app.today()

    # Assert
    assert today == date(2026, 11, 2)


def test_the_apps_lifecycle_works_on_the_store_the_app_was_given() -> None:
    # Setup
    store = stored(an_item(id="a", capture_id="ca"))
    app = an_app(store=store)

    # Execute
    app.lifecycle.set_stage("a", Stage.DOING)

    # Assert
    assert fetched_item(store, "a").stage is Stage.DOING


def test_the_default_fix_handler_works_on_the_store_the_app_was_given() -> None:
    # Setup
    store = stored(an_item(id="a", capture_id="ca"))
    app = an_app(store=store)

    # Execute
    app.fixes.apply(FixAction(FixKind.DONE, "a").encode())

    # Assert
    assert fetched_item(store, "a").stage is Stage.DONE


def test_the_default_fix_handler_and_the_apps_lifecycle_draw_ids_from_one_sequence() -> None:
    # Setup
    store = stored(an_item(id="a", capture_id="ca"), an_item(id="b", capture_id="cb"))
    app = an_app(store=store)

    # Execute
    app.fixes.apply(FixAction(FixKind.DONE, "a").encode())
    app.lifecycle.complete("b")

    # Assert
    assert len({outcome.id for item_id in "ab" for outcome in store.outcomes_for(item_id)}) == 2


def test_an_explicit_lifecycle_replaces_the_default_one() -> None:
    # Setup
    lifecycle = a_lifecycle(stored())

    # Execute
    app = an_app(lifecycle=lifecycle)

    # Assert
    assert app.lifecycle is lifecycle


def test_the_default_fix_handler_uses_an_explicit_lifecycle() -> None:
    # Setup
    store = stored(an_item(id="a", capture_id="ca"))
    app = an_app(store=store, lifecycle=a_lifecycle(store, new_id=lambda: "fixed-id"))

    # Execute
    app.fixes.apply(FixAction(FixKind.DONE, "a").encode())

    # Assert
    assert [outcome.id for outcome in store.outcomes_for("a")] == ["fixed-id"]


def test_the_default_planning_works_on_the_store_the_app_was_given() -> None:
    # Setup
    store = stored(an_item(id="a", capture_id="ca"))
    app = an_app(store=store)

    # Execute
    step = app.planning.add_step("a", "Book the table", lead_days=2)

    # Assert
    assert store.steps_for("a") == [step]
