from stash.llm import LlmBadOutput, LlmDeferred, LlmError, LlmUnavailable


def test_an_unavailable_provider_is_an_llm_error() -> None:
    # Assert
    assert issubclass(LlmUnavailable, LlmError)


def test_a_deferred_call_is_an_unavailable_provider() -> None:
    # Assert
    assert issubclass(LlmDeferred, LlmUnavailable)


def test_bad_output_is_an_llm_error() -> None:
    # Assert
    assert issubclass(LlmBadOutput, LlmError)


def test_bad_output_is_not_an_unavailable_provider() -> None:
    # Assert
    assert not issubclass(LlmBadOutput, LlmUnavailable)
