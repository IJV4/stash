from types import MappingProxyType

from stash.capture.callbacks import RATING_ARGUMENTS, FixAction, FixKind, KeepChoice
from stash.capture.replies import Button, Reply
from stash.domain import Item
from stash.lifecycle.results import Completion

DONE_TEXT = "🎉 Done: {title}"
AGAIN_SUFFIX = " (again)"
RATED_SUFFIX = " · ⭐{rating}"
NOTES_FOOTER = "Tell me notes or takeaways any time."
KEPT_TEXT = "📚 Kept: {title}"
NOT_KEPT_TEXT = "Okay, not keeping {title}."
RATING_LABEL = "⭐{rating}"
KEEP_LABELS = MappingProxyType[KeepChoice, str](
    {KeepChoice.KEEP: "Keep 📚", KeepChoice.NOT_KEEPING: "Not keeping"}
)


def done_reply(completion: Completion) -> Reply:
    headline = DONE_TEXT.format(title=completion.item.title)
    if completion.repeat:
        headline += AGAIN_SUFFIX
    return Reply(
        f"{headline}\n{NOTES_FOOTER}",
        (_rating_row(completion.outcome.id), _keep_row(completion.item)),
    )


def rated_reply(item: Item, rating: int) -> Reply:
    text = DONE_TEXT.format(title=item.title) + RATED_SUFFIX.format(rating=rating)
    return Reply(text, (_keep_row(item),))


def kept_reply(item: Item) -> Reply:
    return Reply((KEPT_TEXT if item.kept else NOT_KEPT_TEXT).format(title=item.title))


def _rating_row(outcome_id: str) -> tuple[Button, ...]:
    return tuple(
        Button(
            RATING_LABEL.format(rating=rating),
            FixAction(FixKind.RATE, outcome_id, argument).encode(),
        )
        for argument, rating in RATING_ARGUMENTS.items()
    )


def _keep_row(item: Item) -> tuple[Button, ...]:
    return tuple(
        Button(KEEP_LABELS[choice], FixAction(FixKind.KEEP, item.id, choice.value).encode())
        for choice in KeepChoice
    )
