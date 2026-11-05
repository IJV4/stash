import asyncio
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime, tzinfo
from typing import assert_never

from stash.capture import (
    QUESTION_PREFIX,
    Deferred,
    Duplicate,
    Filed,
    IsRequest,
    ProcessResult,
)
from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.hermes_adapter.ports import GpuControl, ItemReader, LibraryReader, Retrier
from stash.hermes_adapter.queries import MAX_LIMIT, ItemQuery, item_type_from_text
from stash.lifecycle import MAX_LIBRARY_LIMIT, LibraryQuery
from stash.rendering import (
    NO_ITEMS,
    NOTHING_PENDING,
    SWITCHED_ON,
    gpu_status_line,
    library_line,
    listing_line,
    result_line,
    switched_off_lines,
)

GPU_USAGE = "Usage: /gpu on|off|status"
LINE_CAP = 20
ASK_AGAIN = f" — send it again starting with {QUESTION_PREFIX} to ask"


def _footer(hidden: int, exact: bool) -> str:
    return f"…and {hidden}{'' if exact else '+'} more"


def _text(shown: Sequence[str], hidden: int, exact: bool) -> str:
    return "\n".join([*shown, _footer(hidden, exact)] if hidden else shown)


def _bounded(lines: Sequence[str], exact: bool = True) -> str:
    shown = list(lines[:LINE_CAP])
    hidden = len(lines) - len(shown)
    while len(_text(shown, hidden, exact)) > TELEGRAM_TEXT_LIMIT:
        shown.pop()
        hidden += 1
    return _text(shown, hidden, exact)


def _listing(lines: Sequence[str], cap: int) -> str:
    return _bounded(lines, exact=len(lines) < cap) if lines else NO_ITEMS


def _zone(moment: datetime) -> tzinfo:
    if moment.tzinfo is None:
        raise ValueError("local_now must be timezone-aware")
    return moment.tzinfo


def _retry_line(result: ProcessResult) -> str:
    match result:
        case IsRequest():
            return result_line(result) + ASK_AGAIN
        case Filed() | Deferred() | Duplicate():
            return result_line(result)
        case _:
            assert_never(result)


class ListCommand:
    def __init__(self, reader: ItemReader) -> None:
        self._reader = reader

    async def run(self, raw_args: str) -> str:
        try:
            query = replace(ItemQuery.from_text(raw_args), limit=MAX_LIMIT)
        except ValueError as refusal:
            return str(refusal)
        items = await asyncio.to_thread(query.fetch, self._reader)
        lines = [listing_line(item) for item in items]
        return _listing(lines, MAX_LIMIT)


class LibraryCommand:
    def __init__(self, reader: LibraryReader) -> None:
        self._reader = reader

    async def run(self, raw_args: str) -> str:
        try:
            item_type = item_type_from_text(raw_args)
        except ValueError as refusal:
            return str(refusal)
        query = LibraryQuery(item_type, MAX_LIBRARY_LIMIT)
        entries = await asyncio.to_thread(self._reader.library, query)
        lines = [library_line(entry.item, entry.last_outcome) for entry in entries]
        return _listing(lines, MAX_LIBRARY_LIMIT)


class GpuCommand:
    def __init__(self, switch: GpuControl, local_now: Callable[[], datetime]) -> None:
        self._switch = switch
        self._local_now = local_now

    async def run(self, raw_args: str) -> str:
        match raw_args.lower().split():
            case [] | ["status"]:
                return await asyncio.to_thread(self._status)
            case ["off"]:
                return await asyncio.to_thread(self._off)
            case ["on"]:
                return await asyncio.to_thread(self._on)
            case _:
                return GPU_USAGE

    def _status(self) -> str:
        return gpu_status_line(self._switch.status(self._local_now()))

    def _off(self) -> str:
        now = self._local_now()
        zone = _zone(now)
        return "\n".join(switched_off_lines(self._switch.turn_off(now), zone))

    def _on(self) -> str:
        self._switch.turn_on()
        return SWITCHED_ON


class RetryCommand:
    def __init__(self, steps: Retrier) -> None:
        self._steps = steps

    async def run(self, raw_args: str) -> str:
        results = await asyncio.to_thread(self._steps.retry_pending)
        lines = [_retry_line(result) for result in results]
        return _bounded(lines) if lines else NOTHING_PENDING
