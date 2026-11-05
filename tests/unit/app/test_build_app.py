import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from builders import a_capture, fetched_item
from capture_builders import a_message
from cli_rig import LATE_EVENING_IN_LOS_ANGELES, NOON, CliRig, build_cli_rig
from fakes.search_path import FakeSearchPath
from llm_rig import llm_toml

from stash.app import StashApp, build_app
from stash.capture import Deferred, SerializedPipeline
from stash.capture.callbacks import FixAction, FixKind
from stash.config import ConfigError, StashConfig
from stash.config.loader import load_config
from stash.domain import ItemType, Stage
from stash.evaluation import NoOcr
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


def test_the_app_carries_the_configuration_it_was_built_from(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    config = config_of(rig)

    # Execute
    app = build_app(config, client=rig.providers.client(), run=rig.smi, which=rig.search_path)

    # Assert
    assert app.config is config
    app.close()


def test_building_creates_the_data_directory(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    built(rig).close()

    # Assert
    assert rig.data_dir.is_dir()


def test_the_pipeline_takes_turns_between_handle_process_and_retry(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)

    # Execute
    pipeline = app.pipeline

    # Assert
    assert isinstance(pipeline, SerializedPipeline)
    app.close()


def test_the_pipeline_files_messages_into_the_apps_store(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)

    # Execute
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))

    # Assert
    assert [item.title for item in app.store.list_items()] == ["Ichiran ramen"]
    app.close()


def test_captures_get_distinct_ids(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)

    # Execute
    for number in range(3):
        app.pipeline.handle(a_message("Ramen", message_id=f"m{number}", received_at=rig.now))

    # Assert
    assert (
        len(
            {capture.id for capture in app.store.pending_captures()}
            | {item.capture_id for item in app.store.list_items()}
        )
        == 3
    )
    app.close()


def test_the_fix_handler_edits_items_in_the_apps_store_stamped_with_the_apps_clock(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    item = app.store.list_items()[0]
    rig.now = NOON + timedelta(hours=1)

    # Execute
    app.fixes.apply(FixAction(FixKind.SET_TYPE, item.id, ItemType.BOOK.value).encode())

    # Assert
    edited = app.store.get_item(item.id)
    assert edited is not None
    assert (edited.item_type, edited.updated_at) == (ItemType.BOOK, rig.now)
    app.close()


def test_the_fix_handler_completes_items_in_the_apps_store_stamped_with_the_apps_clock(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    item = app.store.list_items()[0]
    rig.now = NOON + timedelta(hours=1)

    # Execute
    app.fixes.apply(FixAction(FixKind.DONE, item.id).encode())

    # Assert
    [outcome] = app.store.outcomes_for(item.id)
    assert (fetched_item(app.store, item.id).stage, outcome.recorded_at) == (Stage.DONE, rig.now)
    app.close()


def test_the_fix_handler_files_completion_outcomes_under_the_configured_timezone(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    item = app.store.list_items()[0]
    rig.now = LATE_EVENING_IN_LOS_ANGELES

    # Execute
    app.fixes.apply(FixAction(FixKind.DONE, item.id).encode())

    # Assert
    [outcome] = app.store.outcomes_for(item.id)
    assert outcome.completed_on == date(2026, 11, 2)
    app.close()


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


def test_every_call_to_the_burst_factory_gives_a_new_coalescer(tmp_path: Path) -> None:
    # Setup
    app = built(build_cli_rig(tmp_path))

    # Execute
    first, second = app.burst_factory(), app.burst_factory()

    # Assert
    assert first is not second
    app.close()


def test_the_gpu_switch_works_on_the_apps_own_gate(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)

    # Execute
    app.gpu_switch.turn_off(NOON)

    # Assert
    assert app.gpu.status(NOON).busy is True
    app.close()


def test_with_ollama_configured_switching_the_gpu_off_unloads_its_model(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)

    # Execute
    app.gpu_switch.turn_off(NOON)

    # Assert
    assert [request.url.path for request in rig.providers.requests] == ["/api/generate"]
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


def test_with_ollama_configured_the_gate_asks_ollama_what_it_holds(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)

    # Execute
    app.gpu.status(NOON)

    # Assert
    assert [request.url.path for request in rig.providers.requests] == ["/api/ps"]
    app.close()


def test_each_configured_provider_has_an_eval_target_labelled_with_its_model(
    tmp_path: Path,
) -> None:
    # Setup
    app = built(build_cli_rig(tmp_path))

    # Execute
    labels = {target.label for target in app.eval_targets.targets}

    # Assert
    assert labels == {
        "ollama:local-model thinking=default",
        "ollama:local-model thinking=off",
        "openrouter:cloud/model thinking=default",
        "openrouter:cloud/model thinking=off",
    }
    app.close()


def test_without_tesseract_on_the_path_the_ocr_is_the_unavailable_one(tmp_path: Path) -> None:
    # Setup
    app = built(build_cli_rig(tmp_path))

    # Execute
    ocr = app.ocr

    # Assert
    assert isinstance(ocr, NoOcr)
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


def test_closing_the_app_closes_the_database(tmp_path: Path) -> None:
    # Setup
    app = built(build_cli_rig(tmp_path))

    # Execute
    app.close()

    # Assert
    with pytest.raises(sqlite3.ProgrammingError):
        app.store.list_items()


def test_closing_the_app_leaves_the_injected_http_client_open(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    client = rig.providers.client()
    app = built(rig, client=client)

    # Execute
    app.close()

    # Assert
    assert client.is_closed is False


def test_a_database_that_cannot_be_opened_is_a_config_error(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.data_dir.write_text("a file where the data directory should be")

    # Execute / Assert
    with pytest.raises(ConfigError, match="cannot open the database at"):
        built(rig)


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


def test_while_the_app_is_open_the_database_keeps_its_write_ahead_log(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)

    # Execute
    app = built(rig)

    # Assert
    assert (rig.data_dir / "stash.db-wal").exists()
    app.close()


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


def test_the_filer_tells_the_model_the_date_in_the_configured_timezone(tmp_path: Path) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    rig.now = LATE_EVENING_IN_LOS_ANGELES
    app = built(rig)

    # Execute
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))

    # Assert
    prompt = rig.providers.sent_to("/v1/chat/completions")[0].content.decode()
    assert "Today is Monday 2026-11-02." in prompt
    app.close()


def test_the_apps_lifecycle_completes_items_in_the_apps_store_stamped_with_the_apps_clock(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    item = app.store.list_items()[0]
    rig.now = NOON + timedelta(hours=1)

    # Execute
    app.lifecycle.complete(item.id)

    # Assert
    [outcome] = app.store.outcomes_for(item.id)
    assert (fetched_item(app.store, item.id).stage, outcome.recorded_at) == (Stage.DONE, rig.now)
    app.close()


def test_the_apps_lifecycle_files_completions_under_the_configured_timezone(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    item = app.store.list_items()[0]
    rig.now = LATE_EVENING_IN_LOS_ANGELES

    # Execute
    app.lifecycle.complete(item.id)

    # Assert
    [outcome] = app.store.outcomes_for(item.id)
    assert outcome.completed_on == date(2026, 11, 2)
    app.close()


def test_a_completion_pressed_on_a_button_and_a_repeat_made_through_the_app_share_one_history(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_cli_rig(tmp_path)
    app = built(rig)
    app.pipeline.handle(a_message("Ichiran ramen in Fukuoka", received_at=rig.now))
    item = app.store.list_items()[0]

    # Execute
    app.fixes.apply(FixAction(FixKind.DONE, item.id).encode())
    app.lifecycle.complete(item.id)

    # Assert
    assert len({outcome.id for outcome in app.lifecycle.history(item.id).outcomes}) == 2
    app.close()
