from datetime import UTC, datetime
from pathlib import Path

from app_builders import an_app
from builders import stored_item
from cli_session import Session
from eval_builders import an_eval_targets
from eval_files import write_cases
from fakes.ocr import FakeOcr
from fakes.store_factories import FreshStore

from stash.config import Thinking
from stash.domain import ItemType

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


def test_show_reads_the_history_of_the_given_item(tmp_path: Path) -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id="trip", title="Japan trip", item_type=ItemType.PLAN)
    session = Session(tmp_path, an_app(store=store))

    # Execute
    output = at(session, "show", "trip")

    # Assert
    assert output == "Plans · Japan trip · Inbox\n"
