import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import httpx
from builders import an_ollama_settings, chat_body
from config_builders import an_llm_config
from fakes.busy import FakeBusy

from stash.config import ProviderName
from stash.filing import Filer
from stash.llm import ModelRouter
from stash.llm.openai_compat import OpenAICompatibleChat

NOON_UTC = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
FILING_ANSWER = {
    "route": "capture",
    "item_type": "place",
    "title": "Ichiran ramen",
    "stage": "want_to",
    "details": {},
    "tags": [],
    "people": [],
    "date": None,
}
EXPECTED_ENVELOPE = {
    "type": "json_schema",
    "name": "filing",
    "strict": True,
    "required": {
        "route",
        "item_type",
        "title",
        "stage",
        "details",
        "tags",
        "people",
        "date",
    },
    "routes": ["capture", "request", "unsure"],
    "stages": ["inbox", "want_to", "planned"],
}


def filer_over_http(seen: list[httpx.Request]) -> Filer:
    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=chat_body(json.dumps(FILING_ANSWER)))

    client = httpx.Client(transport=httpx.MockTransport(handler))
    chat = OpenAICompatibleChat(an_ollama_settings(), client)
    router = ModelRouter(an_llm_config(), {ProviderName.OLLAMA: chat}, FakeBusy())
    return Filer(router, lambda: NOON_UTC, ZoneInfo("UTC"))


def test_filing_posts_the_filing_schema_as_plain_json_to_the_model() -> None:
    # Setup
    seen: list[httpx.Request] = []
    filer = filer_over_http(seen)

    # Execute
    filer.file("Ichiran ramen in Shibuya", None)

    # Assert
    response_format = json.loads(seen[0].content)["response_format"]
    schema = response_format["json_schema"]["schema"]
    assert {
        "type": response_format["type"],
        "name": response_format["json_schema"]["name"],
        "strict": response_format["json_schema"]["strict"],
        "required": set(schema["required"]),
        "routes": schema["properties"]["route"]["enum"],
        "stages": schema["properties"]["stage"]["enum"],
    } == EXPECTED_ENVELOPE
