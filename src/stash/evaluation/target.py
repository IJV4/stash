from dataclasses import dataclass

from stash.domain import require_text
from stash.llm import ChatModel


@dataclass(frozen=True, slots=True)
class EvalTarget:
    label: str
    model: ChatModel
    vision_model: ChatModel | None = None

    def __post_init__(self) -> None:
        require_text("label", self.label)

    @property
    def image_model(self) -> ChatModel:
        return self.model if self.vision_model is None else self.vision_model
