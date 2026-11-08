import httpx
import pytest
from builders import API_KEY
from http_wire import DEEPLY_NESTED, Wire
from probe_rig import OPENROUTER

from stash.llm import ProbeResult
from stash.llm.probes import OpenRouterModelProbe

MODEL = OPENROUTER.model


def model_check(outcome: httpx.Response | Exception) -> ProbeResult:
    return OpenRouterModelProbe(OPENROUTER, Wire(outcome).client()).check()


def test_the_model_probe_reports_an_unreachable_server() -> None:
    # Execute
    result = model_check(httpx.ConnectError("refused"))

    # Assert
    assert result == ProbeResult(False, "cannot reach OpenRouter at https://openrouter.ai/api/v1")


def test_the_model_probe_does_not_raise_on_a_decoding_error() -> None:
    # Execute
    result = model_check(httpx.DecodingError("bad gzip"))

    # Assert
    assert result == ProbeResult(False, "cannot reach OpenRouter at https://openrouter.ai/api/v1")


def test_the_model_probe_never_puts_the_key_in_the_detail() -> None:
    # Execute
    result = model_check(httpx.ConnectError(f"refused for {API_KEY}"))

    # Assert
    assert API_KEY not in result.detail


@pytest.mark.parametrize(
    "body",
    [
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"models": []}),
        httpx.Response(200, json={"data": "none"}),
        httpx.Response(200, json={"data": {"id": MODEL}}),
        httpx.Response(200, text=DEEPLY_NESTED),
    ],
    ids=["not-json", "array", "no-data-key", "data-not-a-list", "data-an-object", "deeply-nested"],
)
def test_the_model_probe_reports_an_unexpected_response_for_a_malformed_body(
    body: httpx.Response,
) -> None:
    # Execute
    result = model_check(body)

    # Assert
    assert result == ProbeResult(False, "unexpected response from OpenRouter")
