import logging
from typing import Any

import httpx
import pytest
from http_wire import FIVE_SECONDS, Wire
from probe_rig import MALFORMED_BODIES, OLLAMA

from stash.llm.probes import OllamaVramUsage

PROBES_LOGGER = "stash.llm.probes"


MIB = 1024 * 1024
GIB = 1024 * MIB


def running(*size_vram: Any) -> httpx.Response:
    return httpx.Response(200, json={"models": [{"size_vram": size} for size in size_vram]})


def own_mib(outcome: httpx.Response | Exception) -> int:
    return OllamaVramUsage(OLLAMA, Wire(outcome).client()).own_mib()


def test_the_vram_usage_asks_the_native_ps_endpoint_without_the_v1_suffix() -> None:
    # Setup
    wire = Wire(running())

    # Execute
    OllamaVramUsage(OLLAMA, wire.client()).own_mib()

    # Assert
    assert (wire.request.method, str(wire.request.url)) == (
        "GET",
        "http://localhost:11434/api/ps",
    )


def test_the_vram_usage_passes_a_five_second_timeout_with_the_request() -> None:
    # Setup
    wire = Wire(running())

    # Execute
    OllamaVramUsage(OLLAMA, wire.client()).own_mib()

    # Assert
    assert wire.request.extensions["timeout"] == FIVE_SECONDS


def test_the_vram_usage_converts_bytes_to_mebibytes() -> None:
    # Execute
    mib = own_mib(running(4 * GIB))

    # Assert
    assert mib == 4096


def test_the_vram_usage_sums_every_loaded_model() -> None:
    # Execute
    mib = own_mib(running(GIB, 2 * GIB))

    # Assert
    assert mib == 3072


def test_the_vram_usage_rounds_down_after_summing_not_before() -> None:
    # Execute
    mib = own_mib(running(MIB + MIB // 2, MIB + MIB // 2))

    # Assert
    assert mib == 3


def test_no_loaded_models_use_no_vram() -> None:
    # Execute
    mib = own_mib(running())

    # Assert
    assert mib == 0


def test_the_vram_usage_is_zero_when_the_connection_fails() -> None:
    # Execute
    mib = own_mib(httpx.ConnectError("refused"))

    # Assert
    assert mib == 0


def test_the_vram_usage_is_zero_when_the_request_times_out() -> None:
    # Execute
    mib = own_mib(httpx.ReadTimeout("slow"))

    # Assert
    assert mib == 0


def test_the_vram_usage_is_zero_on_a_non_success_status() -> None:
    # Execute
    mib = own_mib(httpx.Response(500, json={"models": [{"size_vram": GIB}]}))

    # Assert
    assert mib == 0


@pytest.mark.parametrize("body", MALFORMED_BODIES.values(), ids=MALFORMED_BODIES.keys())
def test_the_vram_usage_is_zero_for_a_malformed_body(body: httpx.Response) -> None:
    # Execute
    mib = own_mib(body)

    # Assert
    assert mib == 0


@pytest.mark.parametrize(
    "entry",
    [{}, {"size_vram": "big"}, {"size_vram": True}, {"size_vram": -1}, "model"],
    ids=["missing", "string", "bool", "negative", "not-an-object"],
)
def test_the_vram_usage_is_zero_when_a_loaded_model_entry_is_malformed(entry: object) -> None:
    # Setup
    body = httpx.Response(200, json={"models": [{"size_vram": GIB}, entry]})

    # Execute
    mib = own_mib(body)

    # Assert
    assert mib == 0


def test_the_vram_usage_is_zero_on_a_decoding_error() -> None:
    # Execute
    mib = own_mib(httpx.DecodingError("bad gzip"))

    # Assert
    assert mib == 0


def test_the_vram_usage_warns_naming_the_error_class_when_the_connection_fails(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Execute
    own_mib(httpx.ConnectError("refused"))

    # Assert
    assert caplog.record_tuples == [
        (PROBES_LOGGER, logging.WARNING, "Ollama VRAM usage unavailable: ConnectError")
    ]


def test_the_vram_usage_warns_naming_the_error_class_on_a_decoding_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Execute
    own_mib(httpx.DecodingError("bad gzip"))

    # Assert
    assert caplog.record_tuples == [
        (PROBES_LOGGER, logging.WARNING, "Ollama VRAM usage unavailable: DecodingError")
    ]


def test_the_vram_usage_warns_naming_the_status_on_a_non_success_response(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Execute
    own_mib(httpx.Response(500))

    # Assert
    assert caplog.record_tuples == [
        (PROBES_LOGGER, logging.WARNING, "Ollama VRAM usage unavailable: HTTP 500")
    ]


def test_the_vram_usage_warns_about_an_unexpected_response_for_a_malformed_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Execute
    own_mib(httpx.Response(200, text="<html>nope</html>"))

    # Assert
    assert caplog.record_tuples == [
        (PROBES_LOGGER, logging.WARNING, "Ollama VRAM usage unavailable: unexpected response")
    ]


def test_the_vram_usage_does_not_warn_when_the_read_succeeds(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Execute
    own_mib(running(GIB))

    # Assert
    assert caplog.records == []
