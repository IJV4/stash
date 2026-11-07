from pathlib import Path

from cli_rig import build_cli_rig
from planning_builders import DATE_NIGHT_ID, steps_reply, stored_date_night

from stash.config.loader import load_config
from stash.domain import NudgeKind


def test_the_apps_nudge_delivery_records_the_first_tick_in_the_apps_ledger(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = rig.build(load_config(rig.config_file, rig.env))

    # Execute
    app.nudge_delivery.deliver(rig.now, lambda reply: None)

    # Assert
    assert app.store.last_sent(NudgeKind.DIGEST) is not None
    app.close()


def test_the_apps_proposal_delivery_proposes_steps_for_the_planned_items_of_the_apps_store(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = rig.build(load_config(rig.config_file, rig.env))
    stored_date_night(app.store)
    rig.providers.answer = steps_reply(1)

    # Execute
    app.proposal_delivery.deliver(lambda reply: None)

    # Assert
    assert len(app.store.steps_for(DATE_NIGHT_ID)) == 1
    app.close()
