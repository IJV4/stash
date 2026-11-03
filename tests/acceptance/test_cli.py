import io
import json
from contextlib import closing
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from capture_builders import a_filing_answer
from cli_rig import LATE_EVENING_IN_LOS_ANGELES, NOON, CliRig, build_cli_rig
from fakes.backup_source import FakeBackupSource

from stash.cli import main
from stash.store import BackupError
from stash.store.backup import BackupName, Backups
from stash.store.sqlite import SqliteStore

EVERY_SUBCOMMAND = [
    ["doctor"],
    ["list"],
    ["retry"],
    ["gpu", "status"],
    ["eval"],
    ["backup", "--to", "backups"],
]


@pytest.mark.parametrize("command", EVERY_SUBCOMMAND, ids=lambda command: command[0])
def test_an_invalid_configuration_exits_2_and_prints_the_message_on_standard_error(
    tmp_path: Path, command: list[str]
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.config_file.write_text("bogus = 1\n" + rig.config_file.read_text())

    # Execute
    result = rig.run(*command)

    # Assert
    assert (result.exit_code, result.out, result.err) == (
        2,
        "",
        "unknown config key(s): bogus\n",
    )


def test_an_unreadable_configuration_exits_2_and_prints_the_message_on_standard_error(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    missing = tmp_path / "missing.toml"

    # Execute
    result = rig.run_without_config("doctor", "--config", str(missing))

    # Assert
    assert (result.exit_code, result.err) == (2, f"cannot read config file {missing}\n")


def test_a_database_that_cannot_be_opened_exits_2_and_prints_the_message_on_standard_error(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    (tmp_path / "data").write_text("a file where the data directory should be")

    # Execute
    result = rig.run("list")

    # Assert
    assert (result.exit_code, result.err.startswith("cannot open the database at ")) == (2, True)


def file_three_items(rig: CliRig) -> None:
    items = [
        ("Ichiran ramen", "place", "want_to"),
        ("Lemon chicken", "recipe", "want_to"),
        ("Tonkatsu place", "place", "inbox"),
    ]
    for number, (title, item_type, stage) in enumerate(items):
        rig.now = NOON + timedelta(minutes=number)
        rig.providers.answer = a_filing_answer(title=title, item_type=item_type, stage=stage)
        rig.filed(title, message_id=f"m{number}")


def test_list_filters_narrow_the_items_and_the_limit_caps_them(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    file_three_items(rig)

    # Execute
    result = rig.run("list", "--stage", "want_to", "--limit", "1")

    # Assert
    assert (result.exit_code, result.out) == (0, "Recipes · Lemon chicken · Want to\n")


def test_list_with_nothing_to_show_prints_no_items_and_exits_0(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    result = rig.run("list")

    # Assert
    assert (result.exit_code, result.out) == (0, "No items.\n")


def test_retry_files_pending_captures_once_the_gpu_is_free_and_then_finds_nothing_pending(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.smi.busy = True
    rig.filed("Ichiran ramen in Fukuoka")
    rig.smi.busy = False

    # Execute
    first = rig.run("retry")
    second = rig.run("retry")

    # Assert
    assert (first.out, second.out) == (
        "filed — Places · Ichiran ramen · Want to\n",
        "Nothing pending.\n",
    )


def test_retry_while_the_gpu_is_busy_says_deferred_keeps_the_captures_pending_and_exits_0(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.smi.busy = True
    rig.filed("Ichiran ramen in Fukuoka")

    # Execute
    first = rig.run("retry")
    second = rig.run("retry")

    # Assert
    line = "deferred (gpu_busy) — Ichiran ramen in Fukuoka\n"
    assert (first.exit_code, first.out, second.out) == (0, line, line)


def test_gpu_off_prints_the_expiry_unloads_the_model_and_status_then_reads_busy(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    off = rig.run("gpu", "off")
    status = rig.run("gpu", "status")

    # Assert
    unloads = [json.loads(request.content) for request in rig.providers.sent_to("/api/generate")]
    assert (off.out, unloads, status.out) == (
        "GPU switched off until 08:00\n",
        [{"model": "local-model", "keep_alive": 0}],
        "GPU busy — turned off until 08:00\n",
    )


def test_gpu_on_prints_switched_on_and_status_then_reads_free(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.run("gpu", "off")

    # Execute
    on = rig.run("gpu", "on")
    status = rig.run("gpu", "status")

    # Assert
    assert (on.out, status.out) == ("GPU switched on\n", "GPU free — GPU is free\n")


def test_gpu_off_still_switches_the_gate_off_when_ollama_cannot_be_reached(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.providers.ollama_reachable = False

    # Execute
    off = rig.run("gpu", "off")
    status = rig.run("gpu", "status")

    # Assert
    assert (off.exit_code, off.out, status.out) == (
        0,
        "GPU switched off until 08:00\n"
        "! could not unload the model: cannot reach Ollama at http://localhost:11434\n",
        "GPU busy — turned off until 08:00\n",
    )


def test_backup_writes_a_readable_copy_named_for_the_local_date_and_prints_its_path(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.filed("Ichiran ramen in Fukuoka")
    rig.now = LATE_EVENING_IN_LOS_ANGELES
    target = tmp_path / "backups"

    # Execute
    result = rig.run("backup", "--to", str(target))

    # Assert
    written = target / "stash-20261102.db"
    with closing(SqliteStore(written)) as copy:
        titles = [item.title for item in copy.list_items()]
    assert (result.out, titles) == (f"Backup written: {written}\n", ["Ichiran ramen"])


def test_backup_with_31_older_backups_present_leaves_the_newest_30(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    target = tmp_path / "backups"
    target.mkdir()
    today = NOON.date()
    older = [today - timedelta(days=back) for back in range(1, 32)]
    for day in older:
        (target / str(BackupName.for_day(day))).write_bytes(b"old")

    # Execute
    rig.run("backup", "--to", str(target))

    # Assert
    kept = [today, *older[:29]]
    assert {path.name for path in target.glob("stash-*.db")} == {
        str(BackupName.for_day(day)) for day in kept
    }


def test_backup_exits_1_and_prints_the_message_on_standard_error_when_the_source_fails(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    source = FakeBackupSource()
    source.fail_with = BackupError("database is locked")
    target = tmp_path / "backups"
    out, err = io.StringIO(), io.StringIO()

    # Execute
    exit_code = main(
        ["backup", "--to", str(target), "--config", str(rig.config_file)],
        factory=lambda config: replace(rig.build(config), backups=Backups(source)),
        env=rig.env,
        out=out,
        err=err,
    )

    # Assert
    assert (exit_code, out.getvalue(), err.getvalue()) == (
        1,
        "",
        f"cannot write a backup to {target}: database is locked\n",
    )
