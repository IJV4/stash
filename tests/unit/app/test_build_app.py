from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from builders import a_capture
from cli_rig import NOON, CliRig, build_cli_rig
from fakes.search_path import FakeSearchPath
from llm_rig import llm_toml

from stash.app import StashApp, build_app
from stash.capture import Deferred
from stash.config import StashConfig
from stash.config.loader import load_config
from stash.evaluation.tesseract import TesseractOcr

FIVE_SECOND_WINDOW = "burst_window_seconds = 5\n"
OPENROUTER_ONLY = (
    'timezone = "America/Los_Angeles"\n'
    '[llm]\nprovider = "openrouter"\n'
    '[llm.openrouter]\nmodel = "cloud/model"\n'
)


def config_of(rig: CliRig) -> StashConfig:
    return load_config(rig.config_file, rig.env)


def built(rig: CliRig, **overrides: object) -> StashApp:
    return build_app(
        config_of(rig),
        **{
            "client": rig.providers.client(),
            "run": rig.smi,
            "which": rig.search_path,
            "clock": lambda: rig.now,
            **overrides,
        },  # type: ignore[arg-type]
    )


def test_the_burst_coalescer_waits_for_the_configured_window(tmp_path: Path) -> None:
    # Setup
    rig = CliRig(tmp_path, FIVE_SECOND_WINDOW + llm_toml("ollama"))
    app = built(rig)
    bursts = app.burst_factory()
    bursts.add(Deferred(a_capture(), "gpu_busy"), NOON)

    # Execute
    early = bursts.due(NOON + timedelta(seconds=4))
    on_time = bursts.due(NOON + timedelta(seconds=5))

    # Assert
    assert (early is None, on_time is not None) == (True, True)
    app.close()


def test_without_ollama_configured_switching_the_gpu_off_unloads_nothing(tmp_path: Path) -> None:
    # Setup
    rig = CliRig(tmp_path, OPENROUTER_ONLY)
    app = built(rig)

    # Execute
    result = app.gpu_switch.turn_off(NOON)

    # Assert
    assert (result.warnings, rig.providers.requests) == ((), [])
    app.close()


def test_without_ollama_configured_the_gate_does_not_ask_ollama_what_it_holds(
    tmp_path: Path,
) -> None:
    # Setup
    rig = CliRig(tmp_path, OPENROUTER_ONLY)
    app = built(rig)

    # Execute
    app.gpu.status(NOON)

    # Assert
    assert rig.providers.requests == []
    app.close()


def test_with_tesseract_on_the_path_the_ocr_is_tesseract(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.search_path = FakeSearchPath({"tesseract": "/usr/bin/tesseract"})
    app = built(rig)

    # Execute
    ocr = app.ocr

    # Assert
    assert isinstance(ocr, TesseractOcr)
    app.close()


def test_the_doctor_checks_the_injected_tools(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.search_path = FakeSearchPath({"deno": "/usr/bin/deno"})
    app = built(rig)

    # Execute
    lines = {line.name: line.detail for line in app.doctor.run().lines}

    # Assert
    assert lines["deno"] == "/usr/bin/deno"
    app.close()


def test_a_failure_after_the_database_was_opened_closes_it_before_raising(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    def exploding(name: str) -> str | None:
        raise RuntimeError(name)

    # Execute
    with pytest.raises(RuntimeError):
        built(rig, which=exploding)

    # Assert
    assert not (rig.data_dir / "stash.db-wal").exists()


def test_without_an_injected_clock_the_app_tells_the_time_in_utc(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = build_app(
        config_of(rig), client=rig.providers.client(), run=rig.smi, which=rig.search_path
    )

    # Execute
    now = app.clock()

    # Assert
    assert now.utcoffset() == timedelta(0)
    app.close()


def test_without_an_injected_clock_the_app_tells_the_current_time(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = build_app(
        config_of(rig), client=rig.providers.client(), run=rig.smi, which=rig.search_path
    )

    # Execute
    before = datetime.now(UTC)
    now = app.clock()
    after = datetime.now(UTC)

    # Assert
    assert before <= now <= after
    app.close()
