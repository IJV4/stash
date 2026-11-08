import pytest

from stash.nudges import NudgeMessage


def test_a_message_carrying_nothing_is_refused() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="at least one"):
        NudgeMessage((), catch_up=False)
