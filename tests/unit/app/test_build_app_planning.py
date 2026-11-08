from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cli_rig import CliRig, build_cli_rig

from stash.app import StashApp, build_app
from stash.capture import gone
from stash.config.loader import load_config


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
