import asyncio
import threading
from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app_builders import stored
from builders import BASE, a_capture, an_item
from fakes.failing_list_store import FailingListStore
from fakes.memory_store import MemoryStore
from fakes.recording_unloader import RecordingUnloader
from fakes.thread_noting_retrier import ThreadNotingRetrier
from fakes.thread_noting_store import ThreadNotingStore
from gate_rig import a_gate, a_sample

from stash.capture import Deferred, Duplicate, Filed, IsRequest, ProcessResult
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.domain import Item, ItemType, Stage
from stash.gpu_switch import GpuSwitch
from stash.hermes_adapter.commands import GpuCommand, ListCommand, RetryCommand
from stash.llm import LlmUnavailable

LOS_ANGELES = ZoneInfo("America/Los_Angeles")
NOON_IN_LOS_ANGELES = BASE.astimezone(LOS_ANGELES)
USAGE = "Usage: /gpu on|off|status"


def run(command: ListCommand | GpuCommand | RetryCommand, raw_args: str = "") -> str:
    return asyncio.run(command.run(raw_args))


def four_items() -> MemoryStore:
    return stored(
        an_item(id="a", capture_id="ca", title="Ichiran", stage=Stage.WANT_TO, created_at=BASE),
        an_item(
            id="b",
            capture_id="cb",
            title="Lemon chicken",
            item_type=ItemType.RECIPE,
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=1),
        ),
        an_item(
            id="c",
            capture_id="cc",
            title="Tonkatsu",
            stage=Stage.INBOX,
            created_at=BASE.replace(minute=2),
        ),
        an_item(
            id="d",
            capture_id="cd",
            title="Gyoza",
            stage=Stage.WANT_TO,
            created_at=BASE.replace(minute=3),
        ),
    )


def many_items(count: int, title: Callable[[int], str] = "Item {}".format) -> MemoryStore:
    items: list[Item] = [
        an_item(
            id=f"i{number:03}",
            capture_id=f"c{number:03}",
            title=title(number),
            created_at=BASE + timedelta(minutes=number),
        )
        for number in range(count)
    ]
    return stored(*items)


def test_list_prints_one_line_per_item_newest_first() -> None:
    # Execute
    text = run(ListCommand(four_items()))

    # Assert
    assert text == (
        "Places · Gyoza · Want to\n"
        "Places · Tonkatsu · Inbox\n"
        "Recipes · Lemon chicken · Want to\n"
        "Places · Ichiran · Want to"
    )


def test_list_narrows_to_a_stage() -> None:
    # Execute
    text = run(ListCommand(four_items()), "inbox")

    # Assert
    assert text == "Places · Tonkatsu · Inbox"


def test_list_accepts_the_want_to_stage_spelled_with_a_space() -> None:
    # Execute
    text = run(ListCommand(four_items()), "Want To")

    # Assert
    assert text.splitlines() == [
        "Places · Gyoza · Want to",
        "Recipes · Lemon chicken · Want to",
        "Places · Ichiran · Want to",
    ]


def test_list_with_nothing_to_show_says_no_items() -> None:
    # Execute
    text = run(ListCommand(MemoryStore()))

    # Assert
    assert text == "No items."


def test_list_with_an_unknown_stage_names_it_and_lists_the_valid_ones() -> None:
    # Execute
    text = run(ListCommand(four_items()), "soonish")

    # Assert
    assert text == (
        "unknown stage 'soonish' (valid: inbox, want_to, planned, doing, done, dropped)"
    )


def test_list_with_a_5000_character_argument_answers_within_the_telegram_limit() -> None:
    # Execute
    text = run(ListCommand(four_items()), "x" * 5000)

    # Assert
    assert len(text) <= TELEGRAM_TEXT_LIMIT


def test_list_shows_the_date_of_an_item_that_has_one() -> None:
    # Setup
    store = stored(an_item(title="Concert", stage=Stage.PLANNED, date=date(2026, 12, 5)))

    # Execute
    text = run(ListCommand(store))

    # Assert
    assert text == "Places · Concert · Planned · 2026-12-05"


def test_list_keeps_a_title_with_control_characters_on_one_line() -> None:
    # Setup
    store = stored(an_item(title="Ramen\nin\x07Shibuya"))

    # Execute
    text = run(ListCommand(store))

    # Assert
    assert text == "Places · Ramen in Shibuya · Inbox"


def test_list_shows_at_most_20_items_and_counts_the_rest() -> None:
    # Execute
    lines = run(ListCommand(many_items(25))).splitlines()

    # Assert
    assert (len(lines), lines[-1]) == (21, "…and 5 more")


def test_list_shows_the_newest_20_items() -> None:
    # Execute
    lines = run(ListCommand(many_items(25))).splitlines()

    # Assert
    assert lines[0] == "Places · Item 24 · Inbox"


def test_list_says_at_least_when_more_items_exist_than_it_looked_at() -> None:
    # Execute
    lines = run(ListCommand(many_items(80))).splitlines()

    # Assert
    assert lines[-1] == "…and 30+ more"


def test_list_never_exceeds_the_telegram_text_limit() -> None:
    # Execute
    text = run(ListCommand(many_items(30, lambda number: f"{number} " + "x" * 500)))

    # Assert
    assert len(text) <= TELEGRAM_TEXT_LIMIT


def test_list_counts_the_lines_it_had_to_drop_to_fit() -> None:
    # Execute
    lines = run(ListCommand(many_items(30, lambda number: f"{number} " + "x" * 500))).splitlines()

    # Assert
    assert (len(lines) - 1) + int(lines[-1].split()[1].rstrip("+")) == 30


def test_list_reads_the_store_off_the_event_loop_thread() -> None:
    # Setup
    store = ThreadNotingStore()

    async def scenario() -> int:
        await ListCommand(store).run("")
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert [thread != loop_thread for thread in store.threads] == [True]


def test_list_lets_a_failing_store_propagate() -> None:
    # Execute / Assert
    with pytest.raises(Exception, match="database is closed"):
        run(ListCommand(FailingListStore()))


def a_switch(
    store: MemoryStore | None = None, unloader: RecordingUnloader | None = None
) -> GpuSwitch:
    gate = a_gate(a_sample(), store=store)
    return GpuSwitch(gate, RecordingUnloader() if unloader is None else unloader)


def a_gpu_command(switch: GpuSwitch | None = None) -> GpuCommand:
    return GpuCommand(switch or a_switch(), lambda: NOON_IN_LOS_ANGELES)


def test_gpu_with_no_argument_prints_the_status() -> None:
    # Execute
    text = run(a_gpu_command())

    # Assert
    assert text == "GPU free — GPU is free"


def test_gpu_status_prints_the_status() -> None:
    # Execute
    text = run(a_gpu_command(), "status")

    # Assert
    assert text == "GPU free — GPU is free"


def test_gpu_off_prints_the_expiry_in_the_owners_timezone() -> None:
    # Execute
    text = run(a_gpu_command(), "off")

    # Assert
    assert text == "GPU switched off until 08:00"


def test_gpu_off_tells_the_model_to_unload() -> None:
    # Setup
    unloader = RecordingUnloader()

    # Execute
    run(a_gpu_command(a_switch(unloader=unloader)), "off")

    # Assert
    assert unloader.unloads == 1


def test_gpu_off_adds_a_warning_line_when_the_model_could_not_be_unloaded() -> None:
    # Setup
    switch = a_switch(unloader=RecordingUnloader(LlmUnavailable("cannot reach Ollama")))

    # Execute
    text = run(a_gpu_command(switch), "off")

    # Assert
    assert text == (
        "GPU switched off until 08:00\n! could not unload the model: cannot reach Ollama"
    )


def test_gpu_status_after_off_reads_busy_until_the_expiry() -> None:
    # Setup
    command = a_gpu_command()
    run(command, "off")

    # Execute
    text = run(command, "status")

    # Assert
    assert text == "GPU busy — turned off until 08:00"


def test_gpu_on_prints_switched_on() -> None:
    # Execute
    text = run(a_gpu_command(), "on")

    # Assert
    assert text == "GPU switched on"


def test_gpu_on_ends_the_switch_off() -> None:
    # Setup
    command = a_gpu_command()
    run(command, "off")
    run(command, "on")

    # Execute
    text = run(command, "status")

    # Assert
    assert text == "GPU free — GPU is free"


@pytest.mark.parametrize("raw", ["OFF", "Off", "  off  ", "\toff\n"])
def test_gpu_accepts_off_in_any_case_and_with_extra_whitespace(raw: str) -> None:
    # Execute
    text = run(a_gpu_command(), raw)

    # Assert
    assert text == "GPU switched off until 08:00"


@pytest.mark.parametrize("raw", ["banana", "off now", "on off", "--help"])
def test_gpu_with_anything_else_prints_the_usage(raw: str) -> None:
    # Execute
    text = run(a_gpu_command(), raw)

    # Assert
    assert text == USAGE


def test_gpu_with_an_unknown_argument_changes_nothing() -> None:
    # Setup
    unloader = RecordingUnloader()
    command = a_gpu_command(a_switch(unloader=unloader))

    # Execute
    run(command, "banana")

    # Assert
    assert unloader.unloads == 0


def test_gpu_reads_the_local_time_afresh_for_every_command() -> None:
    # Setup
    times = iter([NOON_IN_LOS_ANGELES, NOON_IN_LOS_ANGELES + timedelta(hours=5)])
    command = GpuCommand(a_switch(), lambda: next(times))
    run(command, "off")

    # Execute
    text = run(command, "status")

    # Assert
    assert text == "GPU free — GPU is free"


def test_gpu_refuses_a_local_time_without_a_timezone() -> None:
    # Setup
    naive = datetime(2026, 11, 2, 12, 0)
    command = GpuCommand(a_switch(), lambda: naive)

    # Execute / Assert
    with pytest.raises(ValueError, match="local_now must be timezone-aware"):
        run(command, "off")


def test_gpu_off_unloads_the_model_off_the_event_loop_thread() -> None:
    # Setup
    unloader = RecordingUnloader()
    threads: list[int] = []
    unloader.observers.append(lambda: threads.append(threading.get_ident()))
    command = a_gpu_command(a_switch(unloader=unloader))

    async def scenario() -> int:
        await command.run("off")
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert [thread != loop_thread for thread in threads] == [True]


@pytest.mark.parametrize("raw", ["status", "off", "on"])
def test_gpu_touches_the_gate_off_the_event_loop_thread(raw: str) -> None:
    # Setup
    store = ThreadNotingStore()
    command = a_gpu_command(a_switch(store))

    async def scenario() -> int:
        await command.run(raw)
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert loop_thread not in store.threads


def filed(title: str = "Ramen in Shibuya") -> Filed:
    return Filed(an_item(title=title), unsure=False)


def test_retry_with_nothing_pending_says_so() -> None:
    # Execute
    text = run(RetryCommand(ThreadNotingRetrier()))

    # Assert
    assert text == "Nothing pending."


def test_retry_prints_one_line_for_each_processed_capture() -> None:
    # Setup
    retrier = ThreadNotingRetrier(
        [filed(), Deferred(a_capture(text="Dune by Frank Herbert"), "ai_unavailable")]
    )

    # Execute
    text = run(RetryCommand(retrier))

    # Assert
    assert text == (
        "filed — Places · Ramen in Shibuya · Inbox\n"
        "deferred (ai_unavailable) — Dune by Frank Herbert"
    )


def test_retry_prints_a_request_and_a_duplicate() -> None:
    # Setup
    retrier = ThreadNotingRetrier([IsRequest(a_capture(text="What is a ramen?")), Duplicate()])

    # Execute
    text = run(RetryCommand(retrier))

    # Assert
    assert text == (
        "request — What is a ramen? — send it again starting with ? to ask\n"
        "duplicate — already saved"
    )


def test_retry_ignores_its_arguments() -> None:
    # Execute
    text = run(RetryCommand(ThreadNotingRetrier()), "everything please")

    # Assert
    assert text == "Nothing pending."


def test_retry_shows_at_most_20_lines_and_counts_the_rest() -> None:
    # Setup
    results: list[ProcessResult] = [filed(f"Item {number}") for number in range(23)]

    # Execute
    lines = run(RetryCommand(ThreadNotingRetrier(results))).splitlines()

    # Assert
    assert (len(lines), lines[-1]) == (21, "…and 3 more")


def test_retry_never_exceeds_the_telegram_text_limit() -> None:
    # Setup
    results: list[ProcessResult] = [filed("x" * 500) for _ in range(20)]

    # Execute
    text = run(RetryCommand(ThreadNotingRetrier(results)))

    # Assert
    assert len(text) <= TELEGRAM_TEXT_LIMIT


def test_retry_files_the_pending_captures_off_the_event_loop_thread() -> None:
    # Setup
    retrier = ThreadNotingRetrier()

    async def scenario() -> int:
        await RetryCommand(retrier).run("")
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert [thread != loop_thread for thread in retrier.threads] == [True]
