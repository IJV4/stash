import threading
from pathlib import Path

import httpx
from capture_builders import a_message
from cli_rig import CliRig, build_cli_rig
from fakes.gated_chat import GatedChat
from threads import (
    OVERLAP_GRACE_SECONDS,
    WAIT_LIMIT_SECONDS,
    await_signal,
    start,
    start_announcing,
)

from stash.app import StashApp, build_app
from stash.config.loader import load_config


def app_over(rig: CliRig, client: httpx.Client | None = None) -> StashApp:
    return build_app(
        load_config(rig.config_file, rig.env),
        client=client or rig.providers.client(),
        run=rig.smi,
        which=rig.search_path,
        clock=lambda: rig.now,
    )


def test_an_agent_capture_files_into_the_apps_store(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = app_over(rig)

    # Execute
    app.agent_capture.file("Ichiran ramen in Fukuoka")

    # Assert
    assert [item.title for item in app.store.list_items()] == ["Ichiran ramen"]
    app.close()


def test_an_agent_capture_takes_its_turn_behind_a_telegram_capture(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    gated = GatedChat(rig.providers)
    app = app_over(rig, gated.client())
    contending = threading.Event()

    # Execute
    try:
        telegram = start(lambda: app.pipeline.handle(a_message("Ramen", received_at=rig.now)))
        await_signal(gated.entered)
        agent = start_announcing(contending, lambda: app.agent_capture.file("Tidewater Notes"))
        await_signal(contending)
        gated.overlapped.wait(OVERLAP_GRACE_SECONDS)
        gated.release.set()
        telegram.join(WAIT_LIMIT_SECONDS)
        agent.join(WAIT_LIMIT_SECONDS)
    finally:
        app.close()

    # Assert
    assert gated.max_inside == 1
