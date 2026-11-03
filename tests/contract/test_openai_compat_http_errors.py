import httpx
import pytest
from openai_compat_rig import answering, failure_of, flavours, raising

from stash.config import ProviderSettings
from stash.llm import LlmError, LlmUnavailable


@flavours
@pytest.mark.parametrize("status", [500, 502, 503, 402, 408, 429])
def test_a_retryable_http_status_raises_unavailable(
    settings: ProviderSettings, status: int
) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(status, json={"error": "nope"})))

    # Assert
    assert type(failure) is LlmUnavailable


@flavours
@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_a_rejected_request_raises_llm_error_but_not_unavailable(
    settings: ProviderSettings, status: int
) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(status, json={"error": "nope"})))

    # Assert
    assert type(failure) is LlmError


@flavours
def test_a_server_error_with_an_html_body_raises_unavailable(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(502, text="<html>Bad Gateway</html>")))

    # Assert
    assert type(failure) is LlmUnavailable


@flavours
def test_an_http_error_message_names_the_provider_the_status_and_the_upstream_message(
    settings: ProviderSettings,
) -> None:
    # Setup
    body = {"error": {"code": 503, "message": "model overloaded"}}

    # Execute
    failure = failure_of(settings, answering(httpx.Response(503, json=body)))

    # Assert
    assert str(failure) == f"{settings.name} answered HTTP 503: model overloaded"


@flavours
@pytest.mark.parametrize("code", [500, 502, 402, 408, 429])
def test_an_error_body_inside_http_200_with_a_retryable_code_raises_unavailable(
    settings: ProviderSettings, code: int
) -> None:
    # Setup
    body = {"error": {"code": code, "message": "down"}}

    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json=body)))

    # Assert
    assert type(failure) is LlmUnavailable


@flavours
@pytest.mark.parametrize("code", [400, 401, 403, 404])
def test_an_error_body_inside_http_200_with_a_rejection_code_raises_llm_error_but_not_unavailable(
    settings: ProviderSettings, code: int
) -> None:
    # Setup
    body = {"error": {"code": code, "message": "bad request"}}

    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json=body)))

    # Assert
    assert type(failure) is LlmError


@flavours
@pytest.mark.parametrize(
    "error",
    [{"message": "boom"}, {"code": "502", "message": "boom"}, {"code": True}, "boom"],
    ids=["no-code", "string-code", "bool-code", "string-error"],
)
def test_an_error_body_without_an_int_code_raises_unavailable(
    settings: ProviderSettings, error: object
) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json={"error": error})))

    # Assert
    assert type(failure) is LlmUnavailable


@flavours
def test_a_read_timeout_raises_unavailable(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, raising(httpx.ReadTimeout("slow")))

    # Assert
    assert type(failure) is LlmUnavailable


@flavours
def test_a_connection_error_raises_unavailable(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, raising(httpx.ConnectError("refused")))

    # Assert
    assert type(failure) is LlmUnavailable


@flavours
def test_an_unreachable_provider_error_is_chained_to_the_transport_error(
    settings: ProviderSettings,
) -> None:
    # Setup
    original = httpx.ConnectError("refused")

    # Execute
    failure = failure_of(settings, raising(original))

    # Assert
    assert failure.__cause__ is original


@flavours
def test_a_decoding_error_raises_unavailable(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, raising(httpx.DecodingError("bad gzip")))

    # Assert
    assert type(failure) is LlmUnavailable
