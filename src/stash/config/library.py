import re
from dataclasses import dataclass, field

from stash.config.errors import ConfigError

LIBRARY_TOKEN_VAR = "STASH_LIBRARY_TOKEN"
MIN_TOKEN_LENGTH = 24
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9\-._~]*")
TOKEN_ALPHABET = "A-Z a-z 0-9 - . _ ~"
DEFAULT_BIND = "0.0.0.0"
DEFAULT_PORT = 8765
MIN_PORT = 1
MAX_PORT = 65535


@dataclass(frozen=True, slots=True)
class LibraryConfig:
    bind: str = DEFAULT_BIND
    port: int = DEFAULT_PORT
    token: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not MIN_PORT <= self.port <= MAX_PORT:
            raise ConfigError(f"library.port must be between {MIN_PORT} and {MAX_PORT}")
        if self.token is not None:
            self._require_usable_token(self.token)

    @staticmethod
    def _require_usable_token(token: str) -> None:
        if len(token) < MIN_TOKEN_LENGTH:
            raise ConfigError(f"{LIBRARY_TOKEN_VAR} must be at least {MIN_TOKEN_LENGTH} characters")
        if not TOKEN_PATTERN.fullmatch(token):
            raise ConfigError(f"{LIBRARY_TOKEN_VAR} may only use {TOKEN_ALPHABET}")
