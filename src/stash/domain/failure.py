def describe_failure(error: BaseException) -> str:
    message = " ".join(str(error).split())
    kind = type(error).__name__
    return f"{kind}: {message}" if message else kind
