import json
from pathlib import Path

from builders import stored_item
from cli_rig import LATE_EVENING_IN_LOS_ANGELES, build_cli_rig
from fakes.fake_providers import OLLAMA_CHAT_PATH
from suggestion_builders import CONTEXT, DUNE_ID, a_raw_pick, picks_reply

from stash.app import build_app
from stash.config.loader import load_config
from stash.domain import Pick, Stage
from stash.suggestions import Picked
from stash.suggestions.results import SUGGESTION_LIMIT


def test_the_apps_suggestions_pick_from_the_want_to_items_of_the_apps_store(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = build_app(
        load_config(rig.config_file, rig.env),
        client=rig.providers.client(),
        run=rig.smi,
        which=rig.search_path,
        clock=lambda: rig.now,
    )
    dune = stored_item(app.store, id=DUNE_ID, title="Dune", stage=Stage.WANT_TO)
    rig.providers.answer = picks_reply(a_raw_pick(DUNE_ID, "Quiet Saturday read"))

    # Execute
    answer = app.suggestions.suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Picked((Pick(dune, "Quiet Saturday read"),))
    app.close()


def test_the_apps_suggestions_tell_the_model_the_day_in_the_configured_timezone(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.now = LATE_EVENING_IN_LOS_ANGELES
    app = build_app(
        load_config(rig.config_file, rig.env),
        client=rig.providers.client(),
        run=rig.smi,
        which=rig.search_path,
        clock=lambda: rig.now,
    )
    stored_item(app.store, id=DUNE_ID, stage=Stage.WANT_TO)
    rig.providers.answer = picks_reply()

    # Execute
    app.suggestions.suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    [body] = rig.providers.chat_bodies(OLLAMA_CHAT_PATH)
    assert "Today is Monday 2026-11-02." in json.dumps(body)
    app.close()
