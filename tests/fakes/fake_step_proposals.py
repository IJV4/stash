from collections.abc import Callable, Sequence

from stash.domain import Item
from stash.llm import LlmError
from stash.planning import ProposedStep


def _nothing() -> None:
    return None


class FakeStepProposals:
    def __init__(
        self,
        proposals: Sequence[ProposedStep] = (),
        error: LlmError | None = None,
        while_thinking: Callable[[], object] = _nothing,
    ) -> None:
        self._proposals = tuple(proposals)
        self._error = error
        self._while_thinking = while_thinking
        self.asked_about: list[Item] = []

    def propose(self, item: Item) -> tuple[ProposedStep, ...]:
        self.asked_about.append(item)
        self._while_thinking()
        if self._error is not None:
            raise self._error
        return self._proposals
