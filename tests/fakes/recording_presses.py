from stash.hermes_adapter.callbacks import CallbackPress


class PressLog:
    def __init__(self, log: list[str] | None = None, failure: Exception | None = None) -> None:
        self.presses: list[CallbackPress] = []
        self._log: list[str] = [] if log is None else log
        self._failure = failure

    async def __call__(self, press: CallbackPress) -> None:
        self._log.append("press")
        self.presses.append(press)
        if self._failure is not None:
            raise self._failure
