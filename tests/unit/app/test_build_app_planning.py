from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cli_rig import CliRig, build_cli_rig
from planning_builders import DATE_NIGHT_ID, stored_date_night
from step_builders import a_step

from stash.app import StashApp, build_app
from stash.capture import gone
from stash.config.loader import load_config
from stash.planning import Declines


def app_over(rig: CliRig) -> StashApp:
    return build_app(
        load_config(rig.config_file, rig.env),
        client=rig.providers.client(),
        run=rig.smi,
        which=rig.search_path,
        clock=lambda: rig.now,
    )


@contextmanager
def open_app(tmp_path: Path) -> Iterator[StashApp]:
    app = app_over(build_cli_rig(tmp_path))
    try:
        yield app
    finally:
        app.close()


def test_the_apps_fixes_answer_a_no_steps_press_for_an_unknown_item_with_gone(
    tmp_path: Path,
) -> None:
    # Setup
    with open_app(tmp_path) as app:
        # Execute
        reply = app.fixes.apply("stash:n:ghost")

        # Assert
        assert reply == gone()


def test_the_apps_fixes_confirm_the_proposed_steps_stored_in_the_apps_store(
    tmp_path: Path,
) -> None:
    # Setup
    with open_app(tmp_path) as app:
        stored_date_night(app.store)
        proposed = a_step(item_id=DATE_NIGHT_ID)
        app.store.save_steps(DATE_NIGHT_ID, [proposed])

        # Execute
        app.fixes.apply(f"stash:a:{DATE_NIGHT_ID}")

        # Assert
        assert app.store.open_confirmed_steps() == [proposed.confirmed_now()]


def test_the_apps_fixes_record_a_no_steps_press_as_a_decline_in_the_apps_store(
    tmp_path: Path,
) -> None:
    # Setup
    with open_app(tmp_path) as app:
        item = stored_date_night(app.store)

        # Execute
        app.fixes.apply(f"stash:n:{DATE_NIGHT_ID}")

        # Assert
        assert Declines(app.store).is_declined(item) is True


def test_the_apps_planning_adds_confirmed_steps_to_the_items_of_the_apps_store(
    tmp_path: Path,
) -> None:
    # Setup
    with open_app(tmp_path) as app:
        stored_date_night(app.store)

        # Execute
        step = app.planning.add_step(DATE_NIGHT_ID, "Book the table", lead_days=7)

        # Assert
        assert app.store.steps_for(DATE_NIGHT_ID) == [step]


def test_the_apps_planning_stamps_steps_with_the_apps_clock(tmp_path: Path) -> None:
    # Setup
    with open_app(tmp_path) as app:
        stored_date_night(app.store)

        # Execute
        step = app.planning.add_step(DATE_NIGHT_ID, "Book the table", lead_days=7)

        # Assert
        assert step.created_at == app.clock()
