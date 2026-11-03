import sqlite3
from datetime import timedelta
from pathlib import Path

import pytest
from capture_builders import a_message
from cli_rig import NOON, CliRig, build_cli_rig

from stash.app import StashApp, build_app
from stash.capture import Deferred, Filed, reply_for, type_menu
from stash.config.loader import load_config
from stash.gpu_switch import GpuSwitchResult


def real_app(rig: CliRig) -> StashApp:
    config = load_config(rig.config_file, rig.env)
    return build_app(
        config,
        client=rig.providers.client(),
        run=rig.smi,
        which=rig.search_path,
        clock=lambda: rig.now,
    )


def filed(app: StashApp, rig: CliRig, text: str, message_id: str = "m1") -> Filed:
    result = app.pipeline.handle(a_message(text, message_id=message_id, received_at=rig.now))
    if not isinstance(result, Filed):
        raise AssertionError(f"expected a filed item, got {result!r}")
    return result


def test_handling_a_message_files_it_and_reply_for_gives_the_confirmation(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = real_app(rig)

    # Execute
    result = filed(app, rig, "Ichiran ramen in Fukuoka")

    # Assert
    assert reply_for(result).text == "✅ Places · Want to"
    app.close()


def test_the_burst_coalescer_gives_one_combined_reply_once_the_window_has_passed(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = real_app(rig)
    bursts = app.burst_factory()
    for number in range(3):
        bursts.add(filed(app, rig, f"Ramen {number}", f"m{number}"), rig.now)

    # Execute
    before = bursts.due(NOON + timedelta(seconds=7))
    reply = bursts.due(NOON + timedelta(seconds=8))

    # Assert
    assert (before, reply and reply.text.splitlines()[0]) == (None, "✅ Saved 3 items:")
    app.close()


def test_the_fix_handler_answers_a_type_menu_button_for_a_filed_item(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = real_app(rig)
    result = filed(app, rig, "Ichiran ramen in Fukuoka")

    # Execute
    answer = app.fixes.apply(f"stash:t:{result.item.id}")

    # Assert
    assert answer == type_menu(result.item)
    app.close()


def test_retry_pending_files_what_was_deferred_while_the_gpu_was_busy(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = real_app(rig)
    rig.smi.busy = True
    deferred = app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    rig.smi.busy = False

    # Execute
    retried = app.pipeline.retry_pending()

    # Assert
    assert isinstance(deferred, Deferred)
    assert [type(result) for result in retried] == [Filed]
    app.close()


def test_the_gpu_switch_turns_the_gpu_off_and_reports_when_it_ends_and_that_the_model_unloaded(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = real_app(rig)

    # Execute
    result = app.gpu_switch.turn_off(NOON)

    # Assert
    assert result == GpuSwitchResult(until=NOON + timedelta(hours=4))
    app.close()


def test_closing_the_app_closes_the_database(tmp_path: Path) -> None:
    # Setup
    app = real_app(build_cli_rig(tmp_path))

    # Execute
    app.close()

    # Assert
    with pytest.raises(sqlite3.ProgrammingError):
        app.store.list_items()
