from stash.capture.wording import LINE_LIMIT
from stash.domain import Pick, printable_and_clip

PICK_LINE = "• {title} — {reason}"


def pick_line(pick: Pick) -> str:
    return printable_and_clip(
        PICK_LINE.format(title=pick.item.title, reason=pick.reason), LINE_LIMIT
    )
