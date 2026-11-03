import json
from types import MappingProxyType

import httpx
from openai_compat_rig import HELLO, OLLAMA, SCHEMA_NAME, chat_over, completion

FROZEN_SCHEMA = MappingProxyType(
    {
        "type": "object",
        "properties": MappingProxyType(
            {"kind": MappingProxyType({"type": "string", "enum": ("a", "b")})}
        ),
        "required": ("kind",),
        "anyOf": (
            MappingProxyType({"type": "string"}),
            MappingProxyType({"type": "null"}),
        ),
    }
)
PLAIN_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string", "enum": ["a", "b"]}},
    "required": ["kind"],
    "anyOf": [{"type": "string"}, {"type": "null"}],
}


def test_a_deeply_frozen_schema_is_posted_as_plain_json() -> None:
    # Setup
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return completion("{}")

    # Execute
    chat_over(OLLAMA, handler).complete_json(HELLO, FROZEN_SCHEMA, SCHEMA_NAME)

    # Assert
    assert json.loads(seen[0].content)["response_format"]["json_schema"]["schema"] == PLAIN_SCHEMA
