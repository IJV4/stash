import httpx
import pytest
from builders import API_KEY, an_openrouter_settings
from http_wire import DEEPLY_NESTED, FIVE_SECONDS, Wire
from probe_rig import OPENROUTER

from stash.llm import ProbeResult
from stash.llm.probes import OpenRouterModelProbe

MODEL = OPENROUTER.model


def model_list(*ids: object) -> httpx.Response:
    return httpx.Response(200, json={"data": [{"id": model_id} for model_id in ids]})


def model_check(outcome: httpx.Response | Exception) -> ProbeResult:
    return OpenRouterModelProbe(OPENROUTER, Wire(outcome).client()).check()


def test_the_model_probe_asks_the_models_endpoint_with_the_bearer_token() -> None:
    # Setup
    wire = Wire(model_list(MODEL))

    # Execute
    OpenRouterModelProbe(OPENROUTER, wire.client()).check()

    # Assert
    assert (
        wire.request.method,
        str(wire.request.url),
        wire.request.headers["authorization"],
    ) == ("GET", "https://openrouter.ai/api/v1/models", f"Bearer {API_KEY}")


def test_the_model_probe_tolerates_a_trailing_slash_on_the_base_url() -> None:
    # Setup
    settings = an_openrouter_settings(base_url="https://x.test/api/v1/")
    wire = Wire(model_list(settings.model))

    # Execute
    OpenRouterModelProbe(settings, wire.client()).check()

    # Assert
    assert str(wire.request.url) == "https://x.test/api/v1/models"


def test_the_model_probe_passes_a_five_second_timeout_with_the_request() -> None:
    # Setup
    wire = Wire(model_list(MODEL))

    # Execute
    OpenRouterModelProbe(OPENROUTER, wire.client()).check()

    # Assert
    assert wire.request.extensions["timeout"] == FIVE_SECONDS


def test_the_model_probe_is_ok_when_the_configured_model_is_listed() -> None:
    # Execute
    result = model_check(model_list("other/model", MODEL))

    # Assert
    assert result == ProbeResult(True, f"model {MODEL} is offered by OpenRouter")


def test_the_model_probe_is_not_ok_when_the_configured_model_is_not_listed() -> None:
    # Execute
    result = model_check(model_list("other/model"))

    # Assert
    assert result == ProbeResult(False, f"model {MODEL} is not offered by OpenRouter")


def test_the_model_probe_is_not_ok_for_an_empty_list() -> None:
    # Execute
    result = model_check(model_list())

    # Assert
    assert result == ProbeResult(False, f"model {MODEL} is not offered by OpenRouter")


def test_the_model_probe_matches_the_whole_id_only() -> None:
    # Execute
    result = model_check(model_list(f"{MODEL}:free", f"x/{MODEL}"))

    # Assert
    assert result == ProbeResult(False, f"model {MODEL} is not offered by OpenRouter")


def test_the_model_probe_skips_entries_it_cannot_read_and_still_finds_the_model() -> None:
    # Execute
    result = model_check(model_list("text-only", 7, None, MODEL))

    # Assert
    assert result == ProbeResult(True, f"model {MODEL} is offered by OpenRouter")


def test_the_model_probe_skips_entries_without_an_id() -> None:
    # Setup
    body = httpx.Response(200, json={"data": [{"name": "no id"}, {"id": MODEL}]})

    # Execute
    result = model_check(body)

    # Assert
    assert result == ProbeResult(True, f"model {MODEL} is offered by OpenRouter")


def test_the_model_probe_skips_entries_that_are_not_objects() -> None:
    # Setup
    body = httpx.Response(200, json={"data": ["a/b", [MODEL], {"id": MODEL}]})

    # Execute
    result = model_check(body)

    # Assert
    assert result == ProbeResult(True, f"model {MODEL} is offered by OpenRouter")


def test_the_model_probe_reports_the_http_status_of_a_failure() -> None:
    # Execute
    result = model_check(httpx.Response(503))

    # Assert
    assert result == ProbeResult(False, "OpenRouter answered HTTP 503")


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
