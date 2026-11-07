import html
import re
from collections.abc import Callable, Mapping, Sequence
from typing import TypeVar
from urllib.parse import urlsplit

from stash.domain import MAX_RATING, Item, ItemType, Outcome
from stash.library_html.model import SECTION_LIMIT, LibraryEntry, LibrarySnapshot
from stash.library_html.styles import STYLESHEET

T = TypeVar("T")
DEFAULT_TITLE = "My stash"
GENERATED_FORMAT = "%Y-%m-%d %H:%M %Z"
CONTENT_SECURITY_POLICY = "default-src 'none'; style-src 'unsafe-inline'"
NOTHING_HERE = "Nothing here yet."
NO_REASON = "No reason given."
FILLED_STAR = "★"
EMPTY_STAR = "☆"
KEPT_TYPE_ORDER = (ItemType.RECIPE, ItemType.BOOK, ItemType.PLACE, ItemType.MEDIA)
SAFE_LINK_SCHEMES = ("http", "https")
INERT_COLON = "&#58;"
_SCRIPT_SCHEME = re.compile(r"javascript:", re.IGNORECASE)


def _text(value: str) -> str:
    escaped = html.escape(value, quote=True)
    return _SCRIPT_SCHEME.sub(lambda scheme: scheme.group()[:-1] + INERT_COLON, escaped)


def _is_safe_link(url: str) -> bool:
    return urlsplit(url).scheme.lower() in SAFE_LINK_SCHEMES


def _title(item: Item) -> str:
    title = _text(item.title)
    if item.source_url is None:
        return title
    if not _is_safe_link(item.source_url):
        return f'{title} <span class="meta">{_text(item.source_url)}</span>'
    return f'<a href="{_text(item.source_url)}" rel="noopener noreferrer">{title}</a>'


def _paragraph(css_class: str, text: str | None) -> str:
    return f'<p class="{css_class}">{_text(text)}</p>' if text else ""


def _stars(rating: int) -> str:
    return FILLED_STAR * rating + EMPTY_STAR * (MAX_RATING - rating)


def _outcome_meta(outcome: Outcome) -> str:
    stars = f' <span class="stars">{_stars(outcome.rating)}</span>' if outcome.rating else ""
    return f'{stars} <span class="meta">{outcome.completed_on.isoformat()}</span>'


def _takeaways(outcome: Outcome) -> str:
    items = "".join(f"<li>{_text(takeaway)}</li>" for takeaway in outcome.takeaways)
    return f'<ul class="takeaways">{items}</ul>' if items else ""


def _outcome_details(outcome: Outcome | None) -> tuple[str, str]:
    if outcome is None:
        return "", ""
    return _outcome_meta(outcome), _paragraph("note", outcome.notes) + _takeaways(outcome)


def _entry(entry: LibraryEntry) -> str:
    meta, details = _outcome_details(entry.latest_outcome)
    return (
        f'<li class="entry"><span class="title">{_title(entry.item)}</span>{meta}'
        f"{_paragraph('note', entry.item.note)}{_paragraph('summary', entry.media_notes)}"
        f"{details}</li>"
    )


def _want_to_entry(item: Item) -> str:
    return _entry(LibraryEntry(item, []))


def _dropped_entry(item: Item) -> str:
    reason = _text(item.drop_reason or NO_REASON)
    return f'<li class="entry"><span class="title">{_title(item)}</span> — {reason}</li>'


def _more(hidden: int) -> str:
    return f'<li class="more">…and {hidden} more</li>' if hidden > 0 else ""


def _list(members: Sequence[T], render: Callable[[T], str]) -> str:
    shown = "".join(render(member) for member in members[:SECTION_LIMIT])
    return f"<ul>{shown}{_more(len(members) - SECTION_LIMIT)}</ul>"


def _group(heading: str, members: Sequence[T], render: Callable[[T], str]) -> str:
    return f"<h3>{_text(heading)} ({len(members)})</h3>{_list(members, render)}"


def _type_order(present: Mapping[ItemType, object]) -> list[ItemType]:
    leading = [item_type for item_type in KEPT_TYPE_ORDER if item_type in present]
    rest = [item_type for item_type in ItemType if item_type in present]
    return leading + [item_type for item_type in rest if item_type not in leading]


def _typed_groups(by_type: Mapping[ItemType, list[T]], render: Callable[[T], str]) -> str:
    return "".join(
        _group(item_type.label, by_type[item_type], render) for item_type in _type_order(by_type)
    )


def _done_groups(done_by_year: Mapping[int, list[LibraryEntry]]) -> str:
    return "".join(
        _group(str(year), done_by_year[year], _entry) for year in sorted(done_by_year, reverse=True)
    )


def _dropped_details(dropped: list[Item]) -> str:
    if not dropped:
        return ""
    summary = f"Show {len(dropped)} dropped"
    return f"<details><summary>{summary}</summary>{_list(dropped, _dropped_entry)}</details>"


def _section(name: str, heading: str, content: str) -> str:
    body = content or f'<p class="empty">{NOTHING_HERE}</p>'
    return f'<section id="{name}"><h2>{heading}</h2>{body}</section>'


def _head(title: str) -> str:
    return (
        '<meta charset="utf-8">'
        f'<meta http-equiv="Content-Security-Policy" content="{CONTENT_SECURITY_POLICY}">'
        '<meta name="robots" content="noindex">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_text(title)}</title><style>{STYLESHEET}</style>"
    )


def _counts(snapshot: LibrarySnapshot) -> str:
    kept = sum(len(entries) for entries in snapshot.kept.values())
    done = sum(len(entries) for entries in snapshot.done_by_year.values())
    want_to = sum(len(items) for items in snapshot.want_to.values())
    return f"{kept} kept · {done} done · {want_to} want to · {len(snapshot.dropped)} dropped"


def _header(title: str, snapshot: LibrarySnapshot) -> str:
    generated = snapshot.generated_at.strftime(GENERATED_FORMAT)
    return (
        f"<header><h1>{_text(title)}</h1>"
        f'<p class="meta">{_counts(snapshot)}</p>'
        f'<p class="meta">Generated {generated}</p></header>'
    )


def _sections(snapshot: LibrarySnapshot) -> str:
    return (
        _section("kept", "Kept", _typed_groups(snapshot.kept, _entry))
        + _section("done", "Done", _done_groups(snapshot.done_by_year))
        + _section("want-to", "Want to", _typed_groups(snapshot.want_to, _want_to_entry))
        + _section("dropped", "Dropped", _dropped_details(snapshot.dropped))
    )


def render_library(snapshot: LibrarySnapshot, *, title: str = DEFAULT_TITLE) -> str:
    body = _header(title, snapshot) + f"<main>{_sections(snapshot)}</main>"
    return f'<!doctype html><html lang="en"><head>{_head(title)}</head><body>{body}</body></html>'
