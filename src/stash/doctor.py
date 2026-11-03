import logging
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from stash.domain import describe_failure, require_text
from stash.llm import ProbeResult, ProviderProbe

logger = logging.getLogger(__name__)

PASSED = "✔"
FAILED_REQUIRED = "✖"
FAILED_OPTIONAL = "!"
BLOCKED_EXIT_CODE = 1


@dataclass(frozen=True, slots=True)
class DoctorLine:
    name: str
    ok: bool
    required: bool
    detail: str

    def __post_init__(self) -> None:
        require_text("name", self.name)
        require_text("detail", self.detail)

    @property
    def symbol(self) -> str:
        if self.ok:
            return PASSED
        return FAILED_REQUIRED if self.required else FAILED_OPTIONAL

    @property
    def blocks(self) -> bool:
        return not self.ok and self.required

    def render(self) -> str:
        return f"{self.symbol} {self.name} — {self.detail}"


@dataclass(frozen=True, slots=True)
class DoctorCheck:
    name: str
    required: bool
    probe: ProviderProbe

    def __post_init__(self) -> None:
        require_text("name", self.name)

    @classmethod
    def mandatory(cls, name: str, probe: ProviderProbe) -> Self:
        return cls(name, True, probe)

    @classmethod
    def optional(cls, name: str, probe: ProviderProbe) -> Self:
        return cls(name, False, probe)

    def run(self) -> DoctorLine:
        try:
            result = self.probe.check()
        except Exception as error:
            logger.exception("doctor check %s raised", self.name)
            result = ProbeResult(False, describe_failure(error))
        return DoctorLine(self.name, result.ok, self.required, result.detail)


@dataclass(frozen=True, slots=True)
class DoctorReport:
    lines: tuple[DoctorLine, ...]

    @property
    def blocked(self) -> bool:
        return any(line.blocks for line in self.lines)

    @property
    def exit_code(self) -> int:
        return BLOCKED_EXIT_CODE if self.blocked else 0

    def render(self) -> str:
        return "\n".join(line.render() for line in self.lines)


class Doctor:
    def __init__(self, checks: Sequence[DoctorCheck]) -> None:
        self._checks = tuple(checks)

    def run(self) -> DoctorReport:
        return DoctorReport(tuple(check.run() for check in self._checks))
