from collections.abc import Sequence
from dataclasses import dataclass
from typing import assert_never

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT, FixAction, FixKind
from stash.capture.results import Deferred, Filed
from stash.capture.routing import ASK_AGAIN
from stash.domain import Item, derive_title

TELEGRAM_TEXT_LIMIT = 4096
UTF16_UNIT_BYTES = 2
DETAIL_KEYS = ("city", "author", "platform")
GONE_TEXT = "That item no longer exists."
CHANGED_TEXT = "That changed meanwhile — try again."
BUSY_TEXT = "The stash is busy — try again in a moment."
REFUSED_TEXT = "I can't do that: {message}"
DONE_LABEL = "Done ✓"
RETRY_COMMAND = "/stash_retry"
DEFERRED_TEXT = f"📥 Saved, not filed yet. Send {RETRY_COMMAND} to file it."


# Telegram counts UTF-16 code units, so an emoji outside the BMP counts as 2.
def telegram_length(text: str) -> int:
    return len(text.encode("utf-16-le")) // UTF16_UNIT_BYTES


@dataclass(frozen=True, slots=True)
class Button:
    label: str
    data: str

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("button label must not be blank")
        if len(self.data.encode("utf-8")) > TELEGRAM_CALLBACK_LIMIT:
            raise ValueError(f"button data exceeds {TELEGRAM_CALLBACK_LIMIT} bytes")


@dataclass(frozen=True, slots=True)
class Reply:
    text: str
    buttons: tuple[tuple[Button, ...], ...] = ()

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("reply text must not be blank")
        if telegram_length(self.text) > TELEGRAM_TEXT_LIMIT:
            raise ValueError(f"reply text exceeds {TELEGRAM_TEXT_LIMIT} UTF-16 code units")
        object.__setattr__(self, "buttons", tuple(tuple(row) for row in self.buttons))


def confirmation(item: Item, unsure: bool) -> Reply:
    segments = [item.item_type.label, *_detail(item), item.stage.label]
    rows: list[tuple[Button, ...]] = [
        (
            Button("Type", FixAction(FixKind.TYPE_MENU, item.id).encode()),
            Button("Stage", FixAction(FixKind.STAGE_MENU, item.id).encode()),
        )
    ]
    rows.extend(done_rows(item))
    if unsure:
        question = FixAction(FixKind.QUESTION, item.capture_id).encode()
        rows.append((Button("That was a question →", question),))
    return Reply("✅ " + " · ".join(segments), tuple(rows))


def done_rows(item: Item) -> tuple[tuple[Button, ...], ...]:
    if item.is_done:
        return ()
    return ((Button(DONE_LABEL, FixAction(FixKind.DONE, item.id).encode()),),)


def deferred() -> Reply:
    return Reply(DEFERRED_TEXT)


def gone() -> Reply:
    return Reply(GONE_TEXT)


def changed() -> Reply:
    return Reply(CHANGED_TEXT)


def busy() -> Reply:
    return Reply(BUSY_TEXT)


def refused(message: str) -> Reply:
    return Reply(REFUSED_TEXT.format(message=message))


def reply_for(result: Filed | Deferred) -> Reply:
    match result:
        case Filed():
            return confirmation(result.item, result.unsure)
        case Deferred():
            return deferred()
        case _:
            assert_never(result)


def summary(results: Sequence[Filed | Deferred]) -> Reply:
    return Reply(_within_limit(_header(results), [_bullet(result) for result in results]))


def _header(results: Sequence[Filed | Deferred]) -> str:
    saved = f"✅ Saved {len(results)} items"
    if any(isinstance(result, Deferred) for result in results):
        return f"{saved} (send {RETRY_COMMAND} to file the 📥 ones):"
    return f"{saved}:"


def _bullet(result: Filed | Deferred) -> str:
    match result:
        case Filed():
            return f"• {result.item.summary_line()}{ASK_AGAIN if result.unsure else ''}"
        case Deferred():
            return f"• 📥 {derive_title(result.capture.text)} (not filed yet)"
        case _:
            assert_never(result)


def _within_limit(header: str, bullets: list[str]) -> str:
    full = "\n".join([header, *bullets])
    if telegram_length(full) <= TELEGRAM_TEXT_LIMIT:
        return full
    used = telegram_length(header) + 1 + telegram_length(_more(len(bullets)))
    kept: list[str] = []
    for bullet in bullets:
        used += 1 + telegram_length(bullet)
        if used > TELEGRAM_TEXT_LIMIT:
            break
        kept.append(bullet)
    return "\n".join([header, *kept, _more(len(bullets) - len(kept))])


def _more(count: int) -> str:
    return f"• …and {count} more"


def _detail(item: Item) -> list[str]:
    for key in DETAIL_KEYS:
        value = item.details.get(key, "")
        if value.strip():
            return [value]
    return []
