from stash.llm import ProbeResult


class FakeProviderProbe:
    def __init__(self, outcome: ProbeResult | BaseException) -> None:
        self._outcome = outcome
        self.checks = 0

    def check(self) -> ProbeResult:
        self.checks += 1
        if isinstance(self._outcome, BaseException):
            raise self._outcome
        return self._outcome
