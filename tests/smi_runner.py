from collections.abc import Sequence

SMI_OUTPUT = "12288, 1024, 3\n"


class FakeRunner:
    def __init__(self, output: str = SMI_OUTPUT, error: Exception | None = None) -> None:
        self._output = output
        self._error = error
        self.calls: list[Sequence[str]] = []

    def __call__(self, args: Sequence[str]) -> str:
        self.calls.append(args)
        if self._error is not None:
            raise self._error
        return self._output
