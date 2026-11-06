import logging
from typing import Any

from stash.capture.replies import TELEGRAM_TEXT_LIMIT
from stash.hermes_adapter.ports import AgentCapturer
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNWRITABLE, answering, capture_answer
from stash.hermes_adapter.tool_schema import tool_schema
from stash.hermes_adapter.tool_spec import ToolSpec

logger = logging.getLogger(__name__)

CAPTURE_DESCRIPTION = (
    "Save something new the owner mentions that is not in stash yet (search first); "
    "then use the returned item_id."
)
CAPTURE_SCHEMA: dict[str, Any] = tool_schema(
    "stash_capture",
    CAPTURE_DESCRIPTION,
    {
        "text": {
            "type": "string",
            "maxLength": TELEGRAM_TEXT_LIMIT,
            "description": "What the owner mentioned, in their words.",
        },
        "note": {"type": "string", "description": "Anything else the owner said about it."},
    },
    ["text"],
    subject="Titles",
)


class CaptureTools:
    def __init__(self, capturer: AgentCapturer) -> None:
        self._capturer = capturer

    def specs(self) -> tuple[ToolSpec, ...]:
        return (ToolSpec(CAPTURE_SCHEMA, self.capture),)

    def capture(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._capture, logger)

    def _capture(self, arguments: ToolArguments) -> str:
        return capture_answer(
            self._capturer.file(arguments.required_text("text"), arguments.nullable_text("note"))
        )
