import logging
from dataclasses import dataclass
from datetime import datetime

from stash.domain import require_text
from stash.gpu import GpuGate, GpuStatus
from stash.llm import LlmUnavailable, ModelUnloader

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class GpuSwitchResult:
    until: datetime
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for warning in self.warnings:
            require_text("warnings", warning)


class GpuSwitch:
    def __init__(self, gate: GpuGate, unloader: ModelUnloader) -> None:
        self._gate = gate
        self._unloader = unloader

    def turn_off(self, now: datetime) -> GpuSwitchResult:
        until = self._gate.turn_off(now)
        return GpuSwitchResult(until, self._unload())

    def turn_on(self) -> None:
        self._gate.turn_on()

    def status(self, now: datetime) -> GpuStatus:
        return self._gate.status(now)

    def _unload(self) -> tuple[str, ...]:
        try:
            self._unloader.unload()
        except LlmUnavailable as error:
            logger.warning("could not unload the model: %s", type(error).__name__)
            return (f"could not unload the model: {str(error).strip() or type(error).__name__}",)
        return ()
