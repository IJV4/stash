QUESTION_PREFIX = "?"


def forces_request(text: str) -> bool:
    return text.lstrip().startswith(QUESTION_PREFIX)
