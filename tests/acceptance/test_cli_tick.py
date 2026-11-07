from pathlib import Path

from app_builders import an_app
from cli_session import Session
from fakes.memory_store import MemoryStore
from nudge_builders import (
    SATURDAY_MORNING,
    stored_date_night_with_its_step,
)
from nudge_rig import a_nudge_rig

from stash.app import StashApp

REMINDER_TEXT = "⏰ Book the table — for Date night (Sat Feb 13)\n📅 Date night (Sat Feb 13)"
STEP_REMINDER_TEXT = "⏰ Book the table — for Date night (Sat Feb 13)"
FOLLOW_UP_TEXT = "How was Date night?"


def tick(app: StashApp, directory: Path, *flags: str) -> str:
    session = Session(directory, app)
    session.run("tick", *flags, "--config", str(session.config_file))
    return session.out.getvalue()


def a_stash_with_a_date_night_reminder_due() -> MemoryStore:
    store = MemoryStore()
    stored_date_night_with_its_step(store)
    a_nudge_rig(store).digests_before_were_sent(SATURDAY_MORNING)
    return store


def test_tick_with_nothing_due_prints_nothing_at_all(tmp_path: Path) -> None:
    # Setup
    store = MemoryStore()
    a_nudge_rig(store).digests_before_were_sent(SATURDAY_MORNING)
    app = an_app(store=store, clock=lambda: SATURDAY_MORNING)

    # Execute
    output = tick(app, tmp_path)

    # Assert
    assert output == ""


def test_tick_prints_a_due_reminder_once_and_a_second_tick_prints_nothing(tmp_path: Path) -> None:
    # Setup
    app = an_app(store=a_stash_with_a_date_night_reminder_due(), clock=lambda: SATURDAY_MORNING)

    # Execute
    outputs = (tick(app, tmp_path), tick(app, tmp_path))

    # Assert
    assert outputs == (f"{REMINDER_TEXT}\n", "")


def test_tick_dry_run_prints_what_is_due_but_marks_nothing_so_a_real_tick_still_prints_it(
    tmp_path: Path,
) -> None:
    # Setup
    app = an_app(store=a_stash_with_a_date_night_reminder_due(), clock=lambda: SATURDAY_MORNING)

    # Execute
    outputs = (tick(app, tmp_path, "--dry-run"), tick(app, tmp_path))

    # Assert
    assert outputs == (f"{REMINDER_TEXT}\n", f"{REMINDER_TEXT}\n")
