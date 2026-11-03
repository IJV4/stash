USAGE_ERROR = 2
FAILURE = 1


class CommandFailed(Exception):
    def __init__(self, message: str, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code
