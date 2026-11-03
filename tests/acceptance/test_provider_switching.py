from pathlib import Path

import pytest
from builders import API_KEY, BASE, chat_body
from llm_rig import (
    FREE_GPU,
    OLLAMA_URL,
    OPENROUTER_URL,
    SCHEMA,
    ask,
    build_rig,
    llm_toml,
    replying,
)

from stash.config import LlmTask
from stash.llm import LlmBadOutput, LlmError, LlmUnavailable, ProbeResult


def test_openrouter_provider_sends_requests_to_openrouter_with_the_key_and_attribution_header(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("openrouter"), FREE_GPU)

    # Execute
    ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    request = rig.requests[0]
    assert (
        str(request.url),
        request.headers.get("authorization"),
        request.headers.get("x-openrouter-title"),
    ) == (OPENROUTER_URL, f"Bearer {API_KEY}", "stash")


def test_ollama_provider_sends_requests_to_the_local_server_without_authorization(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)

    # Execute
    ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    request = rig.requests[0]
    assert (str(request.url), request.headers.get("authorization")) == (OLLAMA_URL, None)


def test_a_task_override_sends_only_that_task_to_openrouter(tmp_path: Path) -> None:
    # Setup
    toml = llm_toml("ollama", suggestions="openrouter")
    rig = build_rig(tmp_path, toml, FREE_GPU)

    # Execute
    ask(rig.router.model_for(LlmTask.SUGGESTIONS, BASE))
    ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    assert rig.urls() == [OPENROUTER_URL, OLLAMA_URL]


def test_the_answer_is_requested_as_a_json_schema_named_after_the_callers_schema(
    tmp_path: Path,
) -> None:
    # Setup
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU)

    # Execute
    ask(rig.router.model_for(LlmTask.FILING, BASE), schema_name="filing_v1")

    # Assert
    assert rig.sent_json()["response_format"] == {
        "type": "json_schema",
        "json_schema": {"name": "filing_v1", "strict": True, "schema": SCHEMA},
    }


def test_text_that_is_not_json_is_llm_bad_output(tmp_path: Path) -> None:
    # Setup
    answer = replying(200, chat_body("Sorry, I cannot help with that."))
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU, answer)

    # Execute / Assert
    with pytest.raises(LlmBadOutput):
        ask(rig.router.model_for(LlmTask.FILING, BASE))


def test_a_provider_that_is_down_raises_llm_unavailable(tmp_path: Path) -> None:
    # Setup
    answer = replying(503, {"error": {"code": 503, "message": "overloaded"}})
    rig = build_rig(tmp_path, llm_toml("openrouter"), FREE_GPU, answer)

    # Execute / Assert
    with pytest.raises(LlmUnavailable):
        ask(rig.router.model_for(LlmTask.FILING, BASE))


def test_a_rejected_request_raises_llm_error_that_is_not_llm_unavailable(
    tmp_path: Path,
) -> None:
    # Setup
    answer = replying(400, {"error": {"code": 400, "message": "bad schema"}})
    rig = build_rig(tmp_path, llm_toml("openrouter"), FREE_GPU, answer)

    # Execute
    with pytest.raises(LlmError) as raised:
        ask(rig.router.model_for(LlmTask.FILING, BASE))

    # Assert
    assert not isinstance(raised.value, LlmUnavailable)


def test_the_ollama_doctor_probe_reports_a_configured_model_that_is_not_pulled(
    tmp_path: Path,
) -> None:
    # Setup
    answer = replying(200, {"models": [{"name": "other-model:latest"}]})
    rig = build_rig(tmp_path, llm_toml("ollama"), FREE_GPU, answer)

    # Execute
    result = rig.ollama_probe().check()

    # Assert
    assert (result.ok, "local-model" in result.detail) == (False, True)


def test_the_openrouter_doctor_probe_reads_invalid_key_for_a_rejected_key(
    tmp_path: Path,
) -> None:
    # Setup
    answer = replying(401, {"error": {"code": 401, "message": "No auth credentials found"}})
    rig = build_rig(tmp_path, llm_toml("openrouter"), FREE_GPU, answer)

    # Execute
    result = rig.openrouter_probe().check()

    # Assert
    assert result == ProbeResult(False, "invalid key")
