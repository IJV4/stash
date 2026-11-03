import httpx
import pytest
from http_wire import FIVE_SECONDS, Wire
from probe_rig import OLLAMA

from stash.llm import LlmUnavailable
from stash.llm.probes import OllamaControl


def test_unloading_posts_keep_alive_zero_for_the_configured_model_to_the_generate_endpoint() -> (
    None
):
    # Setup
    wire = Wire(httpx.Response(200, json={"done": True}))

    # Execute
    OllamaControl(OLLAMA, wire.client()).unload()

    # Assert
    assert (wire.request.method, str(wire.request.url), wire.request.content) == (
        "POST",
        "http://localhost:11434/api/generate",
        b'{"model":"llama3:8b","keep_alive":0}',
    )


def test_unloading_passes_a_five_second_timeout_with_the_request() -> None:
    # Setup
    wire = Wire(httpx.Response(200, json={}))

    # Execute
    OllamaControl(OLLAMA, wire.client()).unload()

    # Assert
    assert wire.request.extensions["timeout"] == FIVE_SECONDS


def test_unloading_raises_unavailable_when_the_connection_fails() -> None:
    # Setup
    control = OllamaControl(OLLAMA, Wire(httpx.ConnectError("refused")).client())

    # Execute / Assert
    with pytest.raises(LlmUnavailable, match="cannot reach Ollama"):
        control.unload()


@pytest.mark.parametrize("status", [404, 500])
def test_unloading_raises_unavailable_on_a_non_success_status(status: int) -> None:
    # Setup
    control = OllamaControl(OLLAMA, Wire(httpx.Response(status)).client())

    # Execute / Assert
    with pytest.raises(LlmUnavailable, match=f"HTTP {status}"):
        control.unload()


def test_unloading_raises_unavailable_on_a_decoding_error() -> None:
    # Setup
    control = OllamaControl(OLLAMA, Wire(httpx.DecodingError("bad gzip")).client())

    # Execute / Assert
    with pytest.raises(LlmUnavailable, match="cannot reach Ollama"):
        control.unload()
