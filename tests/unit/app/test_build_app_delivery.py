from datetime import UTC, datetime
from pathlib import Path

from cli_rig import build_cli_rig
from people_builders import a_key_date, stored_person

from stash.config.loader import load_config

NINE_IN_THE_MORNING_ON_NOVEMBER_2 = datetime(2026, 11, 2, 17, 0, tzinfo=UTC)
SUNDAY_DIGEST_TIME = datetime(2026, 11, 8, 18, 0, tzinfo=UTC)


def test_the_apps_nudge_delivery_reminds_of_the_key_dates_in_the_apps_store_at_the_configured_leads(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.config_file.write_text(
        rig.config_file.read_text(encoding="utf-8") + "\n[people]\nlead_days = [1]\n",
        encoding="utf-8",
    )
    app = rig.build(load_config(rig.config_file, rig.env))
    ana = stored_person(app.store, name="Ana", aliases=())
    app.store.save_key_date(a_key_date(person_id=ana.id, month=11, day=3, year=1990))
    app.nudge_delivery.deliver(rig.now, lambda reply: None)
    sent: list[str] = []

    # Execute
    app.nudge_delivery.deliver(
        NINE_IN_THE_MORNING_ON_NOVEMBER_2, lambda reply: sent.append(reply.text)
    )

    # Assert
    assert sent == ["🎂 Ana's birthday in 1 day (Tue Nov 3).\nNo gift ideas saved yet."]
    app.close()


def test_the_apps_weekly_digest_lists_the_key_dates_in_the_apps_store(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = rig.build(load_config(rig.config_file, rig.env))
    ana = stored_person(app.store, name="Ana", aliases=())
    app.store.save_key_date(a_key_date(person_id=ana.id, month=11, day=10, year=1990))
    app.nudge_delivery.deliver(rig.now, lambda reply: None)
    sent: list[str] = []

    # Execute
    app.nudge_delivery.deliver(SUNDAY_DIGEST_TIME, lambda reply: sent.append(reply.text))

    # Assert
    assert "• Tue Nov 10 — 🎂 Ana's birthday" in sent[0].splitlines()
    app.close()
