from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

from builders import BASE, a_capture, an_item

from stash.capture import Deferred, Duplicate, Filed, IsRequest
from stash.domain import Item, ItemType, Stage
from stash.gpu import GpuStatus
from stash.gpu_switch import GpuSwitchResult
from stash.rendering import gpu_status_line, listing_line, result_line, switched_off_lines

LOS_ANGELES = ZoneInfo("America/Los_Angeles")


def a_place(**overrides: Any) -> Item:
    fields: dict[str, Any] = {
        "item_type": ItemType.PLACE,
        "title": "Ramen in Shibuya",
        "stage": Stage.WANT_TO,
    }
    return an_item(**{**fields, **overrides})


def test_a_listing_line_reads_type_title_and_stage() -> None:
    # Execute
    line = listing_line(a_place())

    # Assert
    assert line == "Places · Ramen in Shibuya · Want to"


def test_a_listing_line_appends_the_date_when_the_item_has_one() -> None:
    # Execute
    line = listing_line(a_place(stage=Stage.PLANNED, date=date(2026, 12, 5)))

    # Assert
    assert line == "Places · Ramen in Shibuya · Planned · 2026-12-05"


def test_terminal_control_characters_in_a_title_never_reach_the_line() -> None:
    # Execute
    line = listing_line(a_place(title="Ramen\x1b[31m red\x07"))

    # Assert
    assert line == "Places · Ramen [31m red · Want to"


def test_a_filed_result_line_reads_filed_then_type_title_and_stage() -> None:
    # Execute
    line = result_line(Filed(a_place(stage=Stage.PLANNED, date=date(2026, 12, 5)), unsure=False))

    # Assert
    assert line == "filed — Places · Ramen in Shibuya · Planned"


def test_a_request_result_line_shows_the_start_of_the_text() -> None:
    # Execute
    line = result_line(IsRequest(a_capture(text="what can I do Saturday afternoon?")))

    # Assert
    assert line == "request — what can I do Saturday afternoon?"


def test_a_request_result_line_keeps_only_the_first_60_characters() -> None:
    # Execute
    line = result_line(IsRequest(a_capture(text="q" * 80)))

    # Assert
    assert line == "request — " + "q" * 60


def test_a_deferred_result_line_names_the_reason_and_shows_the_text_on_one_line() -> None:
    # Execute
    line = result_line(Deferred(a_capture(text="Ramen in\nShibuya\t tonight"), "gpu_busy"))

    # Assert
    assert line == "deferred (gpu_busy) — Ramen in Shibuya tonight"


def test_a_deferred_result_line_names_an_unavailable_ai() -> None:
    # Execute
    line = result_line(Deferred(a_capture(text="Ramen"), "ai_unavailable"))

    # Assert
    assert line == "deferred (ai_unavailable) — Ramen"


def test_a_deferred_text_line_never_carries_control_characters() -> None:
    # Execute
    line = result_line(Deferred(a_capture(text="Ramen\x1b[2J now"), "gpu_busy"))

    # Assert
    assert line == "deferred (gpu_busy) — Ramen [2J now"


def test_a_duplicate_result_line_says_it_was_already_saved() -> None:
    # Execute
    line = result_line(Duplicate())

    # Assert
    assert line == "duplicate — already saved"


def test_a_busy_gpu_status_line_reads_gpu_busy_and_the_reason() -> None:
    # Execute
    line = gpu_status_line(GpuStatus(True, "GPU 95% busy"))

    # Assert
    assert line == "GPU busy — GPU 95% busy"


def test_a_free_gpu_status_line_reads_gpu_free_and_the_reason() -> None:
    # Execute
    line = gpu_status_line(GpuStatus(False, "GPU is free"))

    # Assert
    assert line == "GPU free — GPU is free"


def test_the_switched_off_line_shows_the_expiry_in_the_given_timezone() -> None:
    # Execute
    lines = switched_off_lines(GpuSwitchResult(BASE.replace(hour=16)), LOS_ANGELES)

    # Assert
    assert lines == ["GPU switched off until 08:00"]


def test_the_switched_off_lines_add_each_warning_after_the_expiry() -> None:
    # Execute
    lines = switched_off_lines(
        GpuSwitchResult(
            BASE.replace(hour=16), ("could not unload the model: cannot reach Ollama",)
        ),
        LOS_ANGELES,
    )

    # Assert
    assert lines == [
        "GPU switched off until 08:00",
        "! could not unload the model: cannot reach Ollama",
    ]


def test_the_switched_off_lines_print_every_warning_on_its_own_line() -> None:
    # Execute
    lines = switched_off_lines(
        GpuSwitchResult(BASE.replace(hour=16), ("first problem", "second problem")), LOS_ANGELES
    )

    # Assert
    assert lines[1:] == ["! first problem", "! second problem"]
