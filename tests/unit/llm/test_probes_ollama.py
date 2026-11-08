import httpx
import pytest
from builders import an_ollama_settings
from http_wire import Wire
from probe_rig import MALFORMED_BODIES

from stash.llm import ProbeResult
from stash.llm.probes import OllamaProbe


def tags(*names: str) -> httpx.Response:
    return httpx.Response(200, json={"models": [{"name": name} for name in names]})


def ollama_check(outcome: httpx.Response | Exception, model: str = "llama3:8b") -> ProbeResult:
    settings = an_ollama_settings(model=model)
    return OllamaProbe(settings, Wire(outcome).client()).check()


def test_the_ollama_probe_says_it_cannot_reach_ollama_when_the_connection_fails() -> None:
    # Execute
    result = ollama_check(httpx.ConnectError("refused"))

    # Assert
    assert result == ProbeResult(False, "cannot reach Ollama at http://localhost:11434")


def test_the_ollama_probe_does_not_raise_on_a_timeout() -> None:
    # Execute
    result = ollama_check(httpx.ReadTimeout("slow"))

    # Assert
    assert result.ok is False


def test_the_ollama_probe_reports_the_http_status_of_a_failed_request() -> None:
    # Execute
    result = ollama_check(httpx.Response(503))

    # Assert
    assert result == ProbeResult(False, "Ollama at http://localhost:11434 answered HTTP 503")


@pytest.mark.parametrize("body", MALFORMED_BODIES.values(), ids=MALFORMED_BODIES.keys())
def test_the_ollama_probe_reports_an_unexpected_response_for_a_malformed_body(
    body: httpx.Response,
) -> None:
    # Execute
    result = ollama_check(body)

    # Assert
    assert result == ProbeResult(False, "unexpected response from Ollama")


@pytest.mark.parametrize(
    "entry",
    [{"size": 1}, {"name": 5}, "llama3:8b"],
    ids=["no-name", "non-string-name", "not-object"],
)
def test_the_ollama_probe_reports_an_unexpected_response_for_a_malformed_model_entry(
    entry: object,
) -> None:
    # Execute
    result = ollama_check(httpx.Response(200, json={"models": [entry]}))

    # Assert
    assert result == ProbeResult(False, "unexpected response from Ollama")


def test_the_ollama_probe_does_not_raise_on_a_decoding_error() -> None:
    # Execute
    result = ollama_check(httpx.DecodingError("bad gzip"))

    # Assert
    assert result == ProbeResult(False, "cannot reach Ollama at http://localhost:11434")
