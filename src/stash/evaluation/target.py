from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from stash.config import ModelChoice, ProviderName, Thinking
from stash.domain import require_text
from stash.llm import ChatModel


class UnconfiguredProviderError(ValueError):
    def __init__(self, name: str) -> None:
        super().__init__(f"provider {name} is not configured")


@dataclass(frozen=True, slots=True)
class NamedModel:
    name: str
    chat: ChatModel

    def __post_init__(self) -> None:
        require_text("name", self.name)


@dataclass(frozen=True, slots=True)
class EvalTarget:
    choice: ModelChoice
    text: NamedModel
    vision: NamedModel | None = None

    @property
    def label(self) -> str:
        vision_suffix = "" if self.vision is None else f" vision={self.vision.name}"
        return (
            f"{self.choice.provider}:{self.text.name}{vision_suffix}"
            f" thinking={self.choice.thinking}"
        )

    @property
    def model(self) -> ChatModel:
        return self.text.chat

    @property
    def image_model(self) -> ChatModel:
        return self.model if self.vision is None else self.vision.chat


@dataclass(frozen=True, slots=True)
class EvalTargets:
    targets: tuple[EvalTarget, ...]
    configured: Thinking
    _by_choice: dict[ModelChoice, EvalTarget] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        targets = tuple(self.targets)
        by_choice = {target.choice: target for target in targets}
        if len(by_choice) != len(targets):
            duplicated = Counter(target.choice for target in targets).most_common(1)[0][0]
            raise ValueError(f"more than one eval target for {duplicated}")
        _require_every_thinking_value(by_choice)
        object.__setattr__(self, "targets", targets)
        object.__setattr__(self, "_by_choice", by_choice)

    def select(
        self, providers: Sequence[str] | None, thinking: Sequence[Thinking] | None
    ) -> tuple[EvalTarget, ...]:
        present = {choice.provider for choice in self._by_choice}
        names = (
            tuple(name for name in ProviderName if name in present)
            if providers is None
            else _require_configured(providers, present)
        )
        values = (self.configured,) if thinking is None else tuple(dict.fromkeys(thinking))
        return tuple(
            self._by_choice[ModelChoice(name, value)] for name in names for value in values
        )


def _require_configured(
    providers: Sequence[str], present: set[ProviderName]
) -> tuple[ProviderName, ...]:
    names = tuple(dict.fromkeys(providers))
    for name in names:
        if name not in present:
            raise UnconfiguredProviderError(name)
    return tuple(ProviderName(name) for name in names)


def _require_every_thinking_value(by_choice: dict[ModelChoice, EvalTarget]) -> None:
    for provider in {choice.provider for choice in by_choice}:
        for value in Thinking:
            if ModelChoice(provider, value) not in by_choice:
                raise ValueError(f"no eval target for {ModelChoice(provider, value)}")
