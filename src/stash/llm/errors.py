class LlmError(Exception):
    pass


class LlmUnavailable(LlmError):
    pass


class LlmDeferred(LlmUnavailable):
    pass


class LlmBadOutput(LlmError):
    pass
