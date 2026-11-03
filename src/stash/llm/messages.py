from dataclasses import dataclass
from typing import Literal

Role = Literal["system", "user", "assistant"]
DATA_URL_PREFIX = "data:"


@dataclass(frozen=True, slots=True)
class TextPart:
    text: str


@dataclass(frozen=True, slots=True)
class ImagePart:
    data_url: str

    def __post_init__(self) -> None:
        if not self.data_url.startswith(DATA_URL_PREFIX):
            raise ValueError(f"an image part must be a {DATA_URL_PREFIX} URL, never a remote one")


Part = TextPart | ImagePart


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    parts: tuple[Part, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parts", tuple(self.parts))
        if not self.parts:
            raise ValueError("a chat message needs at least one part")

    @classmethod
    def text(cls, role: Role, text: str) -> "ChatMessage":
        return cls(role, (TextPart(text),))
