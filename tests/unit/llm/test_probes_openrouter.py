from typing import Any

import httpx
import pytest
from builders import API_KEY, an_openrouter_settings
from http_wire import DEEPLY_NESTED, FIVE_SECONDS, Wire
from probe_rig import OPENROUTER

from stash.llm import ProbeResult
from stash.llm.probes import OpenRouterProbe


def key_info(limit_remaining: Any) -> httpx.Response:
    return httpx.Response(200, json={"data": {"limit_remaining": limit_remaining}})


def openrouter_check(outcome: httpx.Response | Exception) -> ProbeResult:
    return OpenRouterProbe(OPENROUTER, Wire(outcome).client()).check()


def test_the_openrouter_probe_asks_the_key_endpoint_with_the_bearer_token() -> None:
    # Setup
    wire = Wire(key_info(None))

    # Execute
    OpenRouterProbe(OPENROUTER, wire.client()).check()

    # Assert
    assert (
        wire.request.method,
        str(wire.request.url),
        wire.request.headers["authorization"],
    ) == ("GET", "https://openrouter.ai/api/v1/key", f"Bearer {API_KEY}")


def test_the_openrouter_probe_tolerates_a_trailing_slash_on_the_base_url() -> None:
    # Setup
    settings = an_openrouter_settings(base_url="https://x.test/api/v1/")
    wire = Wire(key_info(None))

    # Execute
    OpenRouterProbe(settings, wire.client()).check()

    # Assert
    assert str(wire.request.url) == "https://x.test/api/v1/key"


def test_the_openrouter_probe_passes_a_five_second_timeout_with_the_request() -> None:
    # Setup
    wire = Wire(key_info(None))

    # Execute
    OpenRouterProbe(OPENROUTER, wire.client()).check()

    # Assert
    assert wire.request.extensions["timeout"] == FIVE_SECONDS


def test_the_openrouter_probe_reports_an_unlimited_key_when_the_limit_is_null() -> None:
    # Execute
    result = openrouter_check(key_info(None))

    # Assert
    assert result == ProbeResult(True, "key is valid; limit remaining: unlimited")


def test_the_openrouter_probe_reports_the_http_status_of_other_failures() -> None:
    # Execute
    result = openrouter_check(httpx.Response(500))

    # Assert
    assert result == ProbeResult(False, "OpenRouter answered HTTP 500")


def test_the_openrouter_probe_reports_an_unreachable_server() -> None:
    # Execute
    result = openrouter_check(httpx.ConnectError("refused"))

    # Assert
    assert result == ProbeResult(False, "cannot reach OpenRouter at https://openrouter.ai/api/v1")


def test_the_openrouter_probe_never_puts_the_key_in_the_detail() -> None:
    # Execute
    result = openrouter_check(httpx.ConnectError(f"refused for {API_KEY}"))

    # Assert
    assert API_KEY not in result.detail


@pytest.mark.parametrize(
    "body",
    [
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"data": {}}),
        httpx.Response(200, json={"data": {"limit_remaining": "lots"}}),
        httpx.Response(200, text=DEEPLY_NESTED),
    ],
    ids=["not-json", "array", "no-limit-field", "non-numeric-limit", "deeply-nested"],
)
def test_the_openrouter_probe_reports_an_unexpected_response_for_a_malformed_body(
    body: httpx.Response,
) -> None:
    # Execute
    result = openrouter_check(body)

    # Assert
    assert result == ProbeResult(False, "unexpected response from OpenRouter")


def test_the_openrouter_probe_without_a_key_is_not_ok() -> None:
    # Setup
    keyless = an_openrouter_settings(api_key=None)

    # Execute
    result = OpenRouterProbe(keyless, Wire(key_info(None)).client()).check()

    # Assert
    assert result == ProbeResult(False, "OPENROUTER_API_KEY is not set")


def test_the_openrouter_probe_without_a_key_sends_no_request() -> None:
    # Setup
    keyless = an_openrouter_settings(api_key=None)
    wire = Wire(key_info(None))

    # Execute
    OpenRouterProbe(keyless, wire.client()).check()

    # Assert
    assert wire.requests == []


def test_the_openrouter_probe_does_not_raise_on_a_decoding_error() -> None:
    # Execute
    result = openrouter_check(httpx.DecodingError("bad gzip"))

    # Assert
    assert result == ProbeResult(False, "cannot reach OpenRouter at https://openrouter.ai/api/v1")
