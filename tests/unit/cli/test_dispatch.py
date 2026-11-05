from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app_builders import NOON, an_app, stored
from builders import BASE, an_item
from cli_session import Session
from eval_builders import an_eval_targets
from eval_files import write_cases
from fakes.backup_source import FakeBackupSource
from fakes.ocr import FakeOcr
from fakes.pending_intake import PendingIntake
from fakes.provider_probe import FakeProviderProbe

from stash.config import Thinking
from stash.doctor import Doctor, DoctorCheck
from stash.domain import ItemType, Stage
from stash.llm import ProbeResult
from stash.store.backup import Backups

LATE_EVENING_IN_LOS_ANGELES = datetime(2026, 11, 3, 3, 0, tzinfo=UTC)
IMAGE_CASE = {
    "id": "i01",
    "arm": "image",
    "text": "save this",
    "image": "card.png",
    "expect": {"route": "capture"},
}


def at(session: Session, *argv: str) -> str:
    session.run(*argv, "--config", str(session.config_file))
    return session.out.getvalue()


def test_list_passes_the_stage_the_type_and_the_limit_to_the_store(tmp_path: Path) -> None:
    # Setup
    store = stored(
        an_item(id="a", capture_id="ca", title="Ichiran", stage=Stage.WANT_TO, created_at=BASE),
        an_item(
            id="b",
            capture_id="cb",
            title="Gyoza",
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=1),
        ),
        an_item(
            id="c",
            capture_id="cc",
            title="Lemon chicken",
            item_type=ItemType.RECIPE,
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=2),
        ),
        an_item(
            id="d",
            capture_id="cd",
            title="Tonkatsu",
            stage=Stage.INBOX,
            created_at=BASE.replace(minute=3),
        ),
    )
    session = Session(tmp_path, an_app(store=store))

    # Execute
    output = at(session, "list", "--stage", "want_to", "--type", "place", "--limit", "1")

    # Assert
    assert output == "Places · Gyoza · Want to\n"


def test_retry_runs_the_apps_pipeline(tmp_path: Path) -> None:
    # Setup
    intake = PendingIntake()
    session = Session(tmp_path, an_app(pipeline=intake))

    # Execute
    at(session, "retry")

    # Assert
    assert intake.calls == ["retry_pending"]


def test_doctor_returns_the_exit_code_of_the_apps_report(tmp_path: Path) -> None:
    # Setup
    failing = Doctor([DoctorCheck("database", True, FakeProviderProbe(ProbeResult(False, "down")))])
    session = Session(tmp_path, an_app(doctor=failing))

    # Execute
    exit_code = session.run("doctor", "--config", str(session.config_file))

    # Assert
    assert (exit_code, session.out.getvalue()) == (1, "✖ database — down\n")


def test_gpu_off_shows_the_expiry_in_the_configured_timezone(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path, an_app(clock=lambda: NOON))

    # Execute
    output = at(session, "gpu", "off")

    # Assert
    assert output == "GPU switched off until 08:00\n"


def test_gpu_status_reads_the_apps_gate_in_the_configured_timezone(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path, an_app(clock=lambda: NOON))
    at(session, "gpu", "off")
    session.out.truncate(0)
    session.out.seek(0)

    # Execute
    output = at(session, "gpu", "status")

    # Assert
    assert output == "GPU busy — turned off until 08:00\n"


def test_gpu_on_switches_the_gpu_on(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path)

    # Execute
    output = at(session, "gpu", "on")

    # Assert
    assert output == "GPU switched on\n"


def test_backup_names_the_file_for_the_date_in_the_configured_timezone(tmp_path: Path) -> None:
    # Setup
    session = Session(
        tmp_path,
        an_app(clock=lambda: LATE_EVENING_IN_LOS_ANGELES, backups=Backups(FakeBackupSource())),
    )
    target = tmp_path / "nas"

    # Execute
    at(session, "backup", "--to", str(target))

    # Assert
    assert [path.name for path in target.iterdir()] == ["stash-20261102.db"]


def eval_header(session: Session, *flags: str) -> str:
    cases = write_cases(session.directory, IMAGE_CASE)
    output = at(session, "eval", "--arms", "ocr", "--cases", str(cases), *flags)
    return next(line for line in output.splitlines() if line.startswith("| metric"))


def test_eval_passes_the_thinking_flag_to_the_target_selection(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path, an_app(eval_targets=an_eval_targets()))

    # Execute
    header = eval_header(session, "--thinking", "default,off")

    # Assert
    assert header == "| metric | ollama:local thinking=default | ollama:local thinking=off |"


def test_eval_without_the_thinking_flag_runs_the_apps_configured_thinking(tmp_path: Path) -> None:
    # Setup
    session = Session(tmp_path, an_app(eval_targets=an_eval_targets(configured=Thinking.OFF)))

    # Execute
    header = eval_header(session)

    # Assert
    assert header == "| metric | ollama:local thinking=off |"


def test_eval_uses_the_apps_targets_and_ocr_and_prints_the_report(tmp_path: Path) -> None:
    # Setup
    ocr = FakeOcr("Lemon chicken")
    session = Session(tmp_path, an_app(eval_targets=an_eval_targets(), ocr=ocr))
    cases = write_cases(tmp_path, IMAGE_CASE)

    # Execute
    output = at(session, "eval", "--arms", "ocr", "--cases", str(cases))

    # Assert
    assert (ocr.paths, "| metric | ollama:local thinking=default |" in output.splitlines()) == (
        [tmp_path / "card.png"],
        True,
    )


def an_unreadable_clock() -> datetime:
    raise AssertionError("the clock was read")


def a_counting_clock(reads: list[datetime]) -> Callable[[], datetime]:
    def clock() -> datetime:
        reads.append(NOON)
        return NOON

    return clock


@pytest.mark.parametrize("argv", [("list",), ("retry",), ("doctor",), ("gpu", "on")])
def test_commands_that_do_not_need_the_time_never_read_the_clock(
    tmp_path: Path, argv: tuple[str, ...]
) -> None:
    # Setup
    session = Session(tmp_path, an_app(clock=an_unreadable_clock))

    # Execute
    exit_code = session.run(*argv, "--config", str(session.config_file))

    # Assert
    assert exit_code == 0


@pytest.mark.parametrize("argv", [("gpu", "status"), ("gpu", "off")])
def test_the_gpu_commands_read_the_clock_once(tmp_path: Path, argv: tuple[str, ...]) -> None:
    # Setup
    reads: list[datetime] = []
    session = Session(tmp_path, an_app(clock=a_counting_clock(reads)))

    # Execute
    session.run(*argv, "--config", str(session.config_file))

    # Assert
    assert len(reads) == 1
