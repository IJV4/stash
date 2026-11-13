from stash.domain import RawCapture

QUESTION_PREFIX = "?"
ASK_AGAIN = f" — send it again starting with {QUESTION_PREFIX} to ask"


def forces_request(text: str) -> bool:
    return text.lstrip().startswith(QUESTION_PREFIX)


def is_forced_request(capture: RawCapture) -> bool:
    return capture.may_be_a_request and forces_request(capture.text)
