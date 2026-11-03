import httpx
from builders import API_KEY
from openai_compat_rig import OPENROUTER, answering, failure_of, flavours, raising

from stash.config import ProviderSettings


def test_the_api_key_never_appears_in_a_transport_error_message() -> None:
    # Setup
    leaky = httpx.ConnectError(f"cannot connect with {API_KEY}")

    # Execute
    failure = failure_of(OPENROUTER, raising(leaky))

    # Assert
    assert API_KEY not in str(failure)


def test_the_api_key_never_appears_in_an_http_error_message_even_if_upstream_echoes_it() -> None:
    # Setup
    body = {"error": {"code": 401, "message": f"invalid key {API_KEY}"}}

    # Execute
    failure = failure_of(OPENROUTER, answering(httpx.Response(401, json=body)))

    # Assert
    assert API_KEY not in str(failure)


def test_the_api_key_never_appears_in_a_raw_text_error_message() -> None:
    # Execute
    failure = failure_of(OPENROUTER, answering(httpx.Response(500, text=f"oops {API_KEY}")))

    # Assert
    assert API_KEY not in str(failure)


def test_the_api_key_never_appears_in_an_error_message_found_inside_http_200() -> None:
    # Setup
    body = {"error": {"code": 502, "message": f"bad gateway for {API_KEY}"}}

    # Execute
    failure = failure_of(OPENROUTER, answering(httpx.Response(200, json=body)))

    # Assert
    assert API_KEY not in str(failure)


def test_a_key_straddling_the_clip_limit_leaves_no_fragment_in_the_message() -> None:
    # Setup
    text = "a" * 195 + API_KEY

    # Execute
    failure = failure_of(OPENROUTER, answering(httpx.Response(500, text=text)))

    # Assert
    assert "sk-or" not in str(failure)


@flavours
def test_upstream_error_text_is_clipped_to_200_characters(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(500, text="x" * 5000)))

    # Assert
    assert str(failure).count("x") == 200


@flavours
def test_upstream_error_message_inside_json_is_clipped_to_200_characters(
    settings: ProviderSettings,
) -> None:
    # Setup
    body = {"error": {"code": 500, "message": "y" * 5000}}

    # Execute
    failure = failure_of(settings, answering(httpx.Response(500, json=body)))

    # Assert
    assert str(failure).count("y") == 200


@flavours
def test_upstream_error_message_inside_http_200_is_clipped_to_200_characters(
    settings: ProviderSettings,
) -> None:
    # Setup
    body = {"error": {"code": 500, "message": "z" * 5000}}

    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json=body)))

    # Assert
    assert str(failure).count("z") == 200
