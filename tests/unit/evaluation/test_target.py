import pytest
from eval_builders import a_named_model, a_named_vision_model, a_target
from fakes.chat_model import FakeChatModel

from stash.config import ProviderName, Thinking
from stash.evaluation import NamedModel


def test_a_named_model_with_a_blank_name_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="name must not be blank"):
        NamedModel("  ", FakeChatModel())


def test_a_target_is_labelled_with_its_provider_model_and_thinking() -> None:
    # Execute
    target = a_target(ProviderName.OLLAMA, Thinking.OFF, a_named_model("local-model"))

    # Assert
    assert target.label == "ollama:local-model thinking=off"


def test_a_target_label_follows_the_choice_thinking_not_the_default() -> None:
    # Execute
    target = a_target(ProviderName.OPENROUTER, Thinking.DEFAULT, a_named_model("cloud/model"))

    # Assert
    assert target.label == "openrouter:cloud/model thinking=default"


def test_a_target_without_a_vision_model_sends_images_to_its_text_model() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    target = a_target(text=a_named_model(chat=model))

    # Assert
    assert target.image_model is model


def test_a_target_with_a_vision_model_sends_images_to_it() -> None:
    # Setup
    vision = FakeChatModel()

    # Execute
    target = a_target(vision=a_named_vision_model(vision))

    # Assert
    assert target.image_model is vision


def test_a_target_exposes_its_text_chat_as_its_model() -> None:
    # Setup
    model = FakeChatModel()

    # Execute
    target = a_target(text=a_named_model(chat=model), vision=a_named_vision_model())

    # Assert
    assert target.model is model


def test_a_target_with_a_vision_model_names_it_in_its_label() -> None:
    # Execute
    target = a_target(
        ProviderName.OLLAMA,
        Thinking.OFF,
        a_named_model("local-model"),
        a_named_vision_model(),
    )

    # Assert
    assert target.label == "ollama:local-model vision=local-vision thinking=off"
