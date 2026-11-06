from fakes.scripted_sender import SendFailed

from stash.capture import Reply


class FailingNudgeSender:
    def __init__(self, failures: int) -> None:
        self._failures = failures

    def __call__(self, reply: Reply) -> None:
        if self._failures > 0:
            self._failures -= 1
            raise SendFailed("telegram is down")
