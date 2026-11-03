from collections.abc import Sequence

FREE_OUTPUT = "24576, 1024, 2\n"
BUSY_OUTPUT = "24576, 20000, 5\n"


class SwitchableSmi:
    def __init__(self, busy: bool = False, installed: bool = True) -> None:
        self.busy = busy
        self.installed = installed

    def __call__(self, args: Sequence[str]) -> str:
        if not self.installed:
            raise FileNotFoundError(args[0])
        return BUSY_OUTPUT if self.busy else FREE_OUTPUT
