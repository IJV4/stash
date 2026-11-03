from datetime import tzinfo

from stash.capture import Deferred, Duplicate, Filed, IsRequest, ProcessResult
from stash.domain import Item, collapse_and_clip
from stash.gpu import GpuStatus
from stash.gpu_switch import GpuSwitchResult

SEPARATOR = " · "
DASH = " — "
EXPIRY_FORMAT = "%H:%M"
TEXT_PREVIEW_CHARS = 60
NO_ITEMS = "No items."
NOTHING_PENDING = "Nothing pending."
SWITCHED_ON = "GPU switched on"


def _printable(text: str) -> str:
    return "".join(character if character.isprintable() else " " for character in text)


def _preview(text: str) -> str:
    return collapse_and_clip(_printable(text), TEXT_PREVIEW_CHARS)


def _summary(item: Item) -> str:
    title = " ".join(_printable(item.title).split())
    return SEPARATOR.join([item.item_type.label, title, item.stage.label])


def listing_line(item: Item) -> str:
    if item.date is None:
        return _summary(item)
    return f"{_summary(item)}{SEPARATOR}{item.date.isoformat()}"


def result_line(result: ProcessResult) -> str:
    match result:
        case Filed(item=item):
            return f"filed{DASH}{_summary(item)}"
        case IsRequest(capture=capture):
            return f"request{DASH}{_preview(capture.text)}"
        case Deferred(capture=capture, reason=reason):
            return f"deferred ({reason}){DASH}{_preview(capture.text)}"
        case Duplicate():
            return f"duplicate{DASH}already saved"


def gpu_status_line(status: GpuStatus) -> str:
    return f"GPU {'busy' if status.busy else 'free'}{DASH}{status.reason}"


def switched_off_lines(result: GpuSwitchResult, timezone: tzinfo) -> list[str]:
    expiry = f"GPU switched off until {result.until.astimezone(timezone):{EXPIRY_FORMAT}}"
    return [expiry, *(f"! {warning}" for warning in result.warnings)]
