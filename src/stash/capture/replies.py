from collections.abc import Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import assert_never

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT, FixAction, FixKind
from stash.capture.results import DeferralReason, Deferred, Filed
from stash.domain import Item, derive_title

TELEGRAM_TEXT_LIMIT = 4096
DETAIL_KEYS = ("city", "author", "platform")
GONE_TEXT = "That item no longer exists."
DEFERRED_TEXT = MappingProxyType[DeferralReason, str](
    {
        "gpu_busy": "📥 Saved — I'll file it when the GPU is free.",
        "ai_unavailable": "📥 Saved — I'll file it once the AI is reachable.",
    }
)


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
        if len(self.text) > TELEGRAM_TEXT_LIMIT:
            raise ValueError(f"reply text exceeds {TELEGRAM_TEXT_LIMIT} characters")
        object.__setattr__(self, "buttons", tuple(tuple(row) for row in self.buttons))


def confirmation(item: Item, unsure: bool) -> Reply:
    segments = [item.item_type.label, *_detail(item), item.stage.label]
    rows: list[tuple[Button, ...]] = [
        (
            Button("Type", FixAction(FixKind.TYPE_MENU, item.id).encode()),
            Button("Stage", FixAction(FixKind.STAGE_MENU, item.id).encode()),
        )
    ]
    if unsure:
        question = FixAction(FixKind.QUESTION, item.capture_id).encode()
        rows.append((Button("That was a question →", question),))
    return Reply("✅ " + " · ".join(segments), tuple(rows))


def deferred(reason: DeferralReason) -> Reply:
    return Reply(DEFERRED_TEXT[reason])


def gone() -> Reply:
    return Reply(GONE_TEXT)


def reply_for(result: Filed | Deferred) -> Reply:
    match result:
        case Filed():
            return confirmation(result.item, result.unsure)
        case Deferred():
            return deferred(result.reason)
        case _:
            assert_never(result)


def summary(results: Sequence[Filed | Deferred]) -> Reply:
    header = f"✅ Saved {len(results)} items:"
    return Reply(_within_limit(header, [_bullet(result) for result in results]))


def _bullet(result: Filed | Deferred) -> str:
    match result:
        case Filed():
            return f"• {result.item.summary_line()}"
        case Deferred():
            return f"• 📥 {derive_title(result.capture.text)} (not filed yet)"
        case _:
            assert_never(result)


def _within_limit(header: str, bullets: list[str]) -> str:
    full = "\n".join([header, *bullets])
    if len(full) <= TELEGRAM_TEXT_LIMIT:
        return full
    used = len(header) + 1 + len(_more(len(bullets)))
    kept: list[str] = []
    for bullet in bullets:
        used += 1 + len(bullet)
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
