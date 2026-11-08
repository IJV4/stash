import datetime as dt
import logging
from collections.abc import Callable, Sequence
from zoneinfo import ZoneInfo

from stash.config import LlmTask
from stash.domain import Filing, Route, require_aware
from stash.enrich.links import LinkInfo
from stash.filing.parse import inbox_filing, parse_filing
from stash.filing.prompt import build_messages
from stash.filing.schema import FILING_SCHEMA, SCHEMA_NAME
from stash.llm import ChatModel, ImagePart, LlmBadOutput, ModelSource

logger = logging.getLogger(__name__)


class Filer:
    def __init__(
        self,
        router: ModelSource,
        clock: Callable[[], dt.datetime],
        timezone: ZoneInfo,
    ) -> None:
        self._router = router
        self._clock = clock
        self._timezone = timezone

    def file(self, text: str, link: LinkInfo | None) -> Filing:
        if not text.strip() and link is None:
            return inbox_filing(text, Route.CAPTURE)
        now = self._now()
        model = self._router.model_for(LlmTask.FILING, now)
        return self._ask(model, text, link, now, ())

    def file_image(self, image: ImagePart, note: str, model: ChatModel) -> Filing:
        return self._ask(model, note, None, self._now(), (image,))

    def _now(self) -> dt.datetime:
        now = self._clock()
        require_aware("clock", now)
        return now

    def _ask(
        self,
        model: ChatModel,
        text: str,
        link: LinkInfo | None,
        now: dt.datetime,
        images: Sequence[ImagePart],
    ) -> Filing:
        today = now.astimezone(self._timezone).date()
        messages = build_messages(text, link, today, images)
        try:
            answer = model.complete_json(messages, FILING_SCHEMA, SCHEMA_NAME)
        except LlmBadOutput as error:
            logger.warning("filing model gave unusable output: %s", type(error).__name__)
            return inbox_filing(text, Route.UNSURE)
        return parse_filing(answer, text)
