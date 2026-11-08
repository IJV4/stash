import pytest

from stash.llm import NoModelToUnload, ProbeResult


@pytest.mark.parametrize("detail", ["", " ", "\n\t"], ids=["empty", "space", "whitespace"])
def test_a_probe_result_with_a_blank_detail_raises_value_error(detail: str) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="detail"):
        ProbeResult(ok=True, detail=detail)


def test_no_model_to_unload_does_nothing_and_does_not_raise() -> None:
    # Execute
    outcome = NoModelToUnload().unload()

    # Assert
    assert outcome is None
