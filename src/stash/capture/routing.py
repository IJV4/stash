from stash.domain import RawCapture

QUESTION_PREFIX = "?"


def forces_request(text: str) -> bool:
    return text.lstrip().startswith(QUESTION_PREFIX)


def is_forced_request(capture: RawCapture) -> bool:
    return capture.may_be_a_request and forces_request(capture.text)
