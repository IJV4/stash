import asyncio
from collections.abc import Callable
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from app_builders import stored
from builders import BASE, a_capture, an_item, days_after, stored_completion
from fakes.failing_list_store import FailingListStore
from fakes.failing_read_store import FailingReadStore
from fakes.recording_unloader import RecordingUnloader
from fakes.store_factories import FreshStore
from fakes.thread_noting_retrier import ThreadNotingRetrier
from gate_rig import a_gate, a_sample
from lifecycle_rig import a_lifecycle

from stash.capture import Duplicate, Filed, IsRequest, ProcessResult
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.domain import Item, ItemType, Stage
from stash.gpu_switch import GpuSwitch
from stash.hermes_adapter.commands import GpuCommand, LibraryCommand, ListCommand, RetryCommand

LOS_ANGELES = ZoneInfo("America/Los_Angeles")
NOON_IN_LOS_ANGELES = BASE.astimezone(LOS_ANGELES)
USAGE = "Usage: /gpu on|off|status"


def run(
    command: ListCommand | GpuCommand | RetryCommand | LibraryCommand, raw_args: str = ""
) -> str:
    return asyncio.run(command.run(raw_args))


def four_items() -> FreshStore:
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


def many_items(count: int, title: Callable[[int], str] = "Item {}".format) -> FreshStore:
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


def test_list_lets_a_failing_store_propagate() -> None:
    # Execute / Assert
    with pytest.raises(Exception, match="database is closed"):
        run(ListCommand(FailingListStore()))


def a_switch(
    store: FreshStore | None = None, unloader: RecordingUnloader | None = None
) -> GpuSwitch:
    gate = a_gate(a_sample(), store=store)
    return GpuSwitch(gate, RecordingUnloader() if unloader is None else unloader)


def a_gpu_command(switch: GpuSwitch | None = None) -> GpuCommand:
    return GpuCommand(switch or a_switch(), lambda: NOON_IN_LOS_ANGELES)


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


def test_gpu_refuses_a_local_time_without_a_timezone() -> None:
    # Setup
    naive = datetime(2026, 11, 2, 12, 0)
    command = GpuCommand(a_switch(), lambda: naive)

    # Execute / Assert
    with pytest.raises(ValueError, match="local_now must be timezone-aware"):
        run(command, "off")


def filed(title: str = "Ramen in Shibuya") -> Filed:
    return Filed(an_item(title=title), unsure=False)


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


def kept_items(*titles: tuple[str, ItemType]) -> FreshStore:
    store = FreshStore()
    for number, (title, item_type) in enumerate(titles):
        stored_completion(
            store,
            f"k{number}",
            completed_on=days_after(number),
            kept=True,
            title=title,
            item_type=item_type,
        )
    return store


def many_kept_items(count: int, title: Callable[[int], str] = "Item {}".format) -> FreshStore:
    return kept_items(*[(title(number), ItemType.BOOK) for number in range(count)])


async def no_html() -> str:
    raise AssertionError("the HTML library was not asked for")


def a_library_command(store: FreshStore) -> LibraryCommand:
    return LibraryCommand(a_lifecycle(store), no_html)


def test_library_with_an_unknown_type_names_it_and_lists_the_labels_in_plain_words() -> None:
    # Execute
    text = run(a_library_command(FreshStore()), "spaceship")

    # Assert
    assert text == (
        "unknown type 'spaceship' "
        "(try: places, recipes, purchases, learning, books, media, ideas, plans, activities, "
        "gifts, other)"
    )


def test_library_with_a_5000_character_argument_answers_within_the_telegram_limit() -> None:
    # Execute
    text = run(a_library_command(FreshStore()), "x" * 5000)

    # Assert
    assert len(text) <= TELEGRAM_TEXT_LIMIT


def test_library_shows_at_most_20_items_and_counts_the_rest() -> None:
    # Execute
    lines = run(a_library_command(many_kept_items(25))).splitlines()

    # Assert
    assert (len(lines), lines[-1]) == (21, "…and 5 more")


def test_library_shows_the_most_recently_finished_20_items() -> None:
    # Execute
    lines = run(a_library_command(many_kept_items(25))).splitlines()

    # Assert
    assert lines[0] == "📚 Books: Item 24 · ⭐4"


def test_library_says_at_least_when_more_items_exist_than_it_looked_at() -> None:
    # Execute
    lines = run(a_library_command(many_kept_items(80))).splitlines()

    # Assert
    assert lines[-1] == "…and 30+ more"


def test_library_says_exactly_when_it_looked_at_everything() -> None:
    # Execute
    lines = run(a_library_command(many_kept_items(49))).splitlines()

    # Assert
    assert lines[-1] == "…and 29 more"


def test_library_never_exceeds_the_telegram_text_limit() -> None:
    # Execute
    text = run(a_library_command(many_kept_items(30, lambda number: f"{number} " + "x" * 100)))

    # Assert
    assert len(text) <= TELEGRAM_TEXT_LIMIT


def test_library_counts_the_lines_it_had_to_drop_to_fit() -> None:
    # Execute
    lines = run(
        a_library_command(many_kept_items(30, lambda number: f"{number} " + "x" * 100))
    ).splitlines()

    # Assert
    assert (len(lines) - 1) + int(lines[-1].split()[1].rstrip("+")) == 30


def test_library_lets_a_failing_store_propagate() -> None:
    # Execute / Assert
    with pytest.raises(Exception, match="database is closed"):
        run(a_library_command(FailingReadStore()))
