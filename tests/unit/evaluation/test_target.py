import pytest
from fakes.chat_model import FakeChatModel

from stash.evaluation import EvalTarget


def test_a_target_with_a_blank_label_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="label must not be blank"):
        EvalTarget("  ", FakeChatModel())


def test_a_target_without_a_vision_model_sends_images_to_its_text_model() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    target = EvalTarget("local", model)

    # Assert
    assert target.image_model is model


def test_a_target_with_a_vision_model_sends_images_to_it() -> None:
    # Setup
    vision = FakeChatModel()

    # Execute
    target = EvalTarget("local", FakeChatModel(), vision)

    # Assert
    assert target.image_model is vision
