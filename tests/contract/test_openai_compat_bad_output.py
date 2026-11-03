import httpx
import pytest
from builders import chat_body
from http_wire import DEEPLY_NESTED
from openai_compat_rig import answering, ask, completion, failure_of, flavours

from stash.config import ProviderSettings
from stash.llm import LlmBadOutput, LlmUnavailable


@flavours
def test_json_object_content_is_returned_as_a_dict(settings: ProviderSettings) -> None:
    # Execute
    answer = ask(settings, answering(completion('{"a": 1}')))

    # Assert
    assert answer == {"a": 1}


@flavours
def test_content_that_is_not_json_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(completion("not json")))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_content_that_is_a_json_array_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(completion("[1, 2]")))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_null_content_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    body = {"choices": [{"message": {"content": None}}]}
    failure = failure_of(settings, answering(httpx.Response(200, json=body)))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_a_body_without_choices_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json={"id": "x"})))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_a_body_with_empty_choices_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json={"choices": []})))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
@pytest.mark.parametrize("body", [[1, 2], 5, "error text"], ids=["array", "number", "string"])
def test_a_json_body_that_is_not_an_object_raises_bad_output(
    settings: ProviderSettings, body: object
) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json=body)))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_a_success_body_that_is_not_json_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, text="<html>hi</html>")))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_an_error_field_that_is_null_beside_a_real_answer_is_not_an_error(
    settings: ProviderSettings,
) -> None:
    # Setup
    body = {"error": None, **chat_body('{"a": 1}')}

    # Execute
    answer = ask(settings, answering(httpx.Response(200, json=body)))

    # Assert
    assert answer == {"a": 1}


@flavours
def test_a_body_whose_only_field_is_a_null_error_raises_bad_output(
    settings: ProviderSettings,
) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, json={"error": None})))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_deeply_nested_model_output_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(completion(DEEPLY_NESTED)))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_a_deeply_nested_success_body_raises_bad_output(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(200, text=DEEPLY_NESTED)))

    # Assert
    assert type(failure) is LlmBadOutput


@flavours
def test_a_deeply_nested_error_body_still_maps_the_http_status(settings: ProviderSettings) -> None:
    # Execute
    failure = failure_of(settings, answering(httpx.Response(503, text=DEEPLY_NESTED)))

    # Assert
    assert type(failure) is LlmUnavailable
