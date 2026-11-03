from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Literal, get_args
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

OPENROUTER_API_KEY_VAR = "OPENROUTER_API_KEY"
BusyFallback = Literal["wait", "openrouter"]
BUSY_FALLBACKS: tuple[BusyFallback, ...] = get_args(BusyFallback)
OPENAI_V1_SUFFIX = "/v1"
HTTP_SCHEMES = ("http", "https")
DEFAULT_BURST_WINDOW_SECONDS = 8.0


class ConfigError(ValueError):
    pass


class ProviderName(StrEnum):
    OLLAMA = "ollama"
    OPENROUTER = "openrouter"


class LlmTask(StrEnum):
    FILING = "filing"
    SUGGESTIONS = "suggestions"
    VISION = "vision"


def _is_unprintable_or_space(character: str) -> bool:
    return character.isspace() or not character.isprintable()


def _check_base_url(name: ProviderName, base_url: str) -> None:
    key = f"llm.{name}.base_url"
    if any(_is_unprintable_or_space(character) for character in base_url):
        raise ConfigError(f"{key} is not a valid URL")
    try:
        parts = urlsplit(base_url)
        _ = parts.port
    except ValueError:
        raise ConfigError(f"{key} is not a valid URL") from None
    if parts.scheme not in HTTP_SCHEMES:
        raise ConfigError(f"{key} must start with http:// or https://")
    if not parts.hostname:
        raise ConfigError(f"{key} must include a host")
    if parts.username is not None or parts.password is not None:
        raise ConfigError(f"{key} must not contain credentials (put secrets in env)")
    if parts.query or parts.fragment:
        raise ConfigError(f"{key} must not contain a query string or fragment")
    if name is ProviderName.OPENROUTER and parts.scheme != "https":
        raise ConfigError(f"{key} must use https")


@dataclass(frozen=True, slots=True)
class ProviderSettings:
    name: ProviderName
    base_url: str
    model: str
    api_key: str | None = field(default=None, repr=False)
    vision_model: str | None = None

    def __post_init__(self) -> None:
        if not self.base_url.strip():
            raise ConfigError(f"llm.{self.name}.base_url must not be blank")
        _check_base_url(self.name, self.base_url)
        if not self.model.strip():
            raise ConfigError(f"llm.{self.name}.model must not be blank")

    @property
    def root_url(self) -> str:
        return self.base_url.rstrip("/").removesuffix(OPENAI_V1_SUFFIX)

    def endpoint(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path}"

    def native_endpoint(self, path: str) -> str:
        return f"{self.root_url}/{path}"


@dataclass(frozen=True, slots=True)
class LlmConfig:
    provider: ProviderName
    busy_fallback: BusyFallback
    providers: Mapping[ProviderName, ProviderSettings]
    tasks: Mapping[LlmTask, ProviderName]

    def __post_init__(self) -> None:
        if self.busy_fallback not in BUSY_FALLBACKS:
            raise ConfigError(f"llm.busy_fallback must be one of {', '.join(BUSY_FALLBACKS)}")
        object.__setattr__(self, "providers", MappingProxyType(dict(self.providers)))
        object.__setattr__(self, "tasks", MappingProxyType(dict(self.tasks)))
        for name in self._used_providers():
            self._require_usable(name)

    def provider_for(self, task: LlmTask) -> ProviderName:
        return self.tasks.get(task, self.provider)

    def _used_providers(self) -> tuple[ProviderName, ...]:
        used = {self.provider, *self.tasks.values()}
        if self.busy_fallback == "openrouter":
            used.add(ProviderName.OPENROUTER)
        return tuple(name for name in ProviderName if name in used)

    def _require_usable(self, name: ProviderName) -> None:
        settings = self.providers.get(name)
        if settings is None:
            raise ConfigError(f"llm.{name} is used but has no [llm.{name}] table")
        if name is ProviderName.OPENROUTER and not settings.api_key:
            raise ConfigError(f"llm.openrouter is used but {OPENROUTER_API_KEY_VAR} is not set")


@dataclass(frozen=True, slots=True)
class GpuConfig:
    min_free_vram_mib: int = 9000
    max_foreign_utilization_pct: int = 30
    manual_off_hours: float = 4.0

    def __post_init__(self) -> None:
        if self.min_free_vram_mib < 0:
            raise ConfigError("gpu.min_free_vram_mib must be >= 0")
        if not 0 <= self.max_foreign_utilization_pct <= 100:
            raise ConfigError("gpu.max_foreign_utilization_pct must be between 0 and 100")
        if not self.manual_off_hours > 0:
            raise ConfigError("gpu.manual_off_hours must be > 0")


@dataclass(frozen=True, slots=True)
class StashConfig:
    data_dir: Path
    timezone: ZoneInfo
    llm: LlmConfig
    gpu: GpuConfig
    burst_window_seconds: float = DEFAULT_BURST_WINDOW_SECONDS

    def __post_init__(self) -> None:
        if not self.data_dir.is_absolute():
            raise ConfigError(f"data_dir must be an absolute path, got {self.data_dir}")
        if not self.burst_window_seconds >= 0:
            raise ConfigError("burst_window_seconds must be >= 0")

    @property
    def db_path(self) -> Path:
        return self.data_dir / "stash.db"
