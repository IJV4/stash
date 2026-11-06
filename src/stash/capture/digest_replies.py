from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Self, assert_never

from stash.capture.pick_lines import pick_line
from stash.capture.replies import TELEGRAM_TEXT_LIMIT, Reply
from stash.capture.wording import LINE_LIMIT, short_day
from stash.domain import collapse_and_clip
from stash.nudges.digest import UpcomingEntry, UpcomingItem, UpcomingStep
from stash.nudges.due import WeeklyDigest

DIGEST_HEADER = "🗞 Your weekly digest"
NEW_HEADING = "🆕 New this week"
FORGOTTEN_HEADING = "🕰 Forgotten"
UPCOMING_HEADING = "📅 Coming up"
PICKS_HEADING = "💡 Ideas for this week"
BULLET_LINE = "• {title}"
UPCOMING_ITEM_LINE = "• {day} — {title}"
UPCOMING_STEP_LINE = "• {day} — {text} ({title})"
STUCK_LINE = "📖 How is {title} going?"
MORE_LINE = "…and {count} more"
NEW_CAP = 5
UPCOMING_CAP = 8
STUCK_CAP = 10


class _Part(StrEnum):
    NEW = "new"
    FORGOTTEN = "forgotten"
    UPCOMING = "upcoming"
    STUCK = "stuck"
    PICKS = "picks"


_RENDER_ORDER = (_Part.NEW, _Part.FORGOTTEN, _Part.UPCOMING, _Part.STUCK, _Part.PICKS)
_SHRINKING_ORDER = (_Part.PICKS, _Part.NEW, _Part.UPCOMING)


@dataclass(frozen=True, slots=True)
class _Section:
    heading: str | None
    lines: tuple[str, ...]
    shown: int

    @classmethod
    def of(cls, heading: str | None, lines: Iterable[str], cap: int | None = None) -> Self:
        clipped = tuple(collapse_and_clip(line, LINE_LIMIT) for line in lines)
        return cls(heading, clipped, len(clipped) if cap is None else min(cap, len(clipped)))

    def with_one_line_fewer(self) -> Self:
        return replace(self, shown=self.shown - 1)

    def rendered(self) -> list[str]:
        if not self.lines:
            return []
        hidden = len(self.lines) - self.shown
        heading = [] if self.heading is None else [self.heading]
        more = [MORE_LINE.format(count=hidden)] if hidden else []
        return [*heading, *self.lines[: self.shown], *more]


def render_digest(digest: WeeklyDigest) -> Reply:
    return Reply(_text(_fitted(_sections(digest))))


def _fitted(sections: Mapping[_Part, _Section]) -> Mapping[_Part, _Section]:
    if len(_text(sections)) <= TELEGRAM_TEXT_LIMIT:
        return sections
    giving_way = next((part for part in _SHRINKING_ORDER if sections[part].shown > 0), None)
    if giving_way is None:
        return sections
    return _fitted({**sections, giving_way: sections[giving_way].with_one_line_fewer()})


def _sections(digest: WeeklyDigest) -> Mapping[_Part, _Section]:
    found = digest.sections
    return {
        _Part.NEW: _Section.of(
            NEW_HEADING, (BULLET_LINE.format(title=item.title) for item in found.new_items), NEW_CAP
        ),
        _Part.FORGOTTEN: _Section.of(
            FORGOTTEN_HEADING, (BULLET_LINE.format(title=item.title) for item in found.forgotten)
        ),
        _Part.UPCOMING: _Section.of(
            UPCOMING_HEADING, (_upcoming_line(entry) for entry in found.upcoming), UPCOMING_CAP
        ),
        _Part.STUCK: _Section.of(
            None, (STUCK_LINE.format(title=stuck.item.title) for stuck in digest.stuck), STUCK_CAP
        ),
        _Part.PICKS: _Section.of(PICKS_HEADING, (pick_line(pick) for pick in found.picks)),
    }


def _upcoming_line(entry: UpcomingEntry) -> str:
    day = short_day(entry.on)
    match entry:
        case UpcomingItem():
            return UPCOMING_ITEM_LINE.format(day=day, title=entry.item.title)
        case UpcomingStep():
            return UPCOMING_STEP_LINE.format(day=day, text=entry.step.text, title=entry.item.title)
        case _:
            assert_never(entry)


def _lines(sections: Mapping[_Part, _Section]) -> list[str]:
    return [DIGEST_HEADER, *(line for part in _RENDER_ORDER for line in sections[part].rendered())]


def _text(sections: Mapping[_Part, _Section]) -> str:
    return "\n".join(_lines(sections))
