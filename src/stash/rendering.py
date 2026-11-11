from datetime import tzinfo

from stash.capture import Deferred, Duplicate, Filed, IsRequest, ProcessResult
from stash.capture.occasions import occasion_noun
from stash.capture.wording import short_day
from stash.domain import Item, Outcome, PersonSummary, printable_and_clip, replace_non_printable
from stash.gpu import GpuStatus
from stash.gpu_switch import GpuSwitchResult
from stash.lifecycle import ItemHistory

SEPARATOR = " · "
DASH = " — "
EXPIRY_FORMAT = "%H:%M"
TEXT_PREVIEW_CHARS = 60
NO_ITEMS = "No items."
NO_PEOPLE = "No people yet."
NO_UPCOMING_PEOPLE = "No key dates coming up."
NOTHING_PENDING = "Nothing pending."
NO_SUGGESTIONS = "Nothing to suggest right now."
SUGGESTIONS_UNAVAILABLE = "Suggestions are unavailable right now."
SWITCHED_ON = "GPU switched on"
LIBRARY_PREFIX = "📚"
IN_LIBRARY_MARK = f"{LIBRARY_PREFIX} in library"
GROUP_HEADING = "In this group:"
INDENT = "  "
BULLET = "• "


def _preview(text: str) -> str:
    return printable_and_clip(text, TEXT_PREVIEW_CHARS)


def _clean(text: str) -> str:
    return " ".join(replace_non_printable(text).split())


def _stars(rating: int) -> str:
    return f"⭐{rating}"


def _summary(item: Item) -> str:
    return SEPARATOR.join([item.item_type.label, _clean(item.title), item.stage.label])


def listing_line(item: Item) -> str:
    if item.date is None:
        return _summary(item)
    return f"{_summary(item)}{SEPARATOR}{item.date.isoformat()}"


def person_line(summary: PersonSummary) -> str:
    person = summary.person
    name = _clean(person.name)
    heading = f"{name} ({_clean(person.relation)})" if person.relation else name
    if summary.next_date is None:
        return heading
    occasion = _clean(occasion_noun(summary.next_date.key_date))
    return f"{heading}{DASH}{occasion} {short_day(summary.next_date.on)}"


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


def library_line(item: Item, last_outcome: Outcome | None) -> str:
    line = f"{LIBRARY_PREFIX} {item.item_type.label}: {_clean(item.title)}"
    if last_outcome is None or last_outcome.rating is None:
        return line
    return f"{line}{SEPARATOR}{_stars(last_outcome.rating)}"


def history_lines(history: ItemHistory) -> list[str]:
    item = history.item
    lines = [_item_heading(item)]
    if item.drop_reason:
        lines.append(f"Dropped because: {_clean(item.drop_reason)}")
    if item.source_url:
        lines.append(f"Link: {_clean(item.source_url)}")
    lines.extend(f"{_clean(key)}: {_clean(value)}" for key, value in item.details.items())
    for outcome in history.outcomes:
        lines.extend(_outcome_lines(outcome))
    if history.children:
        lines.append(GROUP_HEADING)
        lines.extend(f"{INDENT}{listing_line(child)}" for child in history.children)
    return lines


def _item_heading(item: Item) -> str:
    line = listing_line(item)
    return f"{line}{SEPARATOR}{IN_LIBRARY_MARK}" if item.in_library else line


def _outcome_lines(outcome: Outcome) -> list[str]:
    heading = f"Done {outcome.completed_on.isoformat()}"
    if outcome.rating is not None:
        heading = f"{heading}{SEPARATOR}{_stars(outcome.rating)}"
    notes = _clean(outcome.notes)
    lines = [heading, f"{INDENT}{notes}"] if notes else [heading]
    lines.extend(f"{INDENT}{BULLET}{_clean(takeaway)}" for takeaway in outcome.takeaways)
    return lines
