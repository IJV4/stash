import json
import logging

from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNWRITABLE, answering
from stash.planning.errors import UnknownItem

LOGGER = logging.getLogger("tests.tool_json_steps")


def refusing_with(error: Exception) -> str:
    def work(arguments: ToolArguments) -> str:
        raise error

    return answering({}, UNWRITABLE, work, LOGGER)


def test_an_unknown_item_is_answered_as_an_error_naming_it() -> None:
    # Execute
    answer = refusing_with(UnknownItem("ghost"))

    # Assert
    assert json.loads(answer) == {"error": "no item 'ghost'"}
