import pytest
from capture_builders import a_filing_answer
from capture_rig import build_rig

from stash.llm import LlmUnavailable


def test_scripted_outcomes_cannot_be_combined_with_an_answer() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="outcomes replaces answer and error"):
        build_rig(answer=a_filing_answer(), outcomes=[a_filing_answer()])


def test_scripted_outcomes_cannot_be_combined_with_an_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="outcomes replaces answer and error"):
        build_rig(error=LlmUnavailable("down"), outcomes=[a_filing_answer()])


def test_setting_a_reply_on_a_rig_built_with_outcomes_fails_loudly() -> None:
    # Setup
    rig = build_rig(outcomes=[a_filing_answer()])

    # Execute / Assert
    with pytest.raises(TypeError, match="built with outcomes="):
        rig.set_reply(a_filing_answer())
