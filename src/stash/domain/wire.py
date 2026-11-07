SEPARATOR = ":"
MAX_ID_LENGTH = 40


def is_wire_safe(part: str) -> bool:
    return (
        part != ""
        and part.isascii()
        and part.isprintable()
        and not any(character.isspace() for character in part)
        and SEPARATOR not in part
    )


def require_wire_safe_id(name: str, value: str, max_length: int = MAX_ID_LENGTH) -> None:
    if not is_wire_safe(value):
        raise ValueError(f"{name} must be non-blank, printable ASCII, without whitespace or ':'")
    if len(value) > max_length:
        raise ValueError(f"{name} must be at most {max_length} characters")
