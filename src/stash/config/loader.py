import tomllib
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from stash.config._section import Section, _Choice
from stash.config.errors import ConfigError
from stash.config.model import (
    BUSY_FALLBACKS,
    DEFAULT_BURST_WINDOW_SECONDS,
    OPENROUTER_API_KEY_VAR,
    WHEN_UNREADABLE_CHOICES,
    GpuConfig,
    LlmConfig,
    LlmTask,
    ProviderName,
    ProviderSettings,
    StashConfig,
    Thinking,
)
from stash.config.nudges import NudgeConfig, Weekday
from stash.config.people import PeopleConfig

DEFAULT_TIMEZONE = "America/Los_Angeles"
DEFAULT_BASE_URLS = MappingProxyType(
    {
        ProviderName.OLLAMA: "http://localhost:11434/v1",
        ProviderName.OPENROUTER: "https://openrouter.ai/api/v1",
    }
)
SECRETS_IN_ENV = "put secrets in env, not in the config file"
HOME_VAR = "HOME"
XDG_DATA_HOME_VAR = "XDG_DATA_HOME"
HOME_PREFIX = "~"
DEFAULT_DATA_SUBPATH = Path(".local/share/stash")
APP_DIR_NAME = "stash"


def load_config(path: Path, env: Mapping[str, str]) -> StashConfig:
    root = Section("", _read_toml(path))
    data_dir = _data_dir(root, env)
    timezone = _timezone(root)
    burst_window_seconds = root.take_number("burst_window_seconds", DEFAULT_BURST_WINDOW_SECONDS)
    llm = _llm_config(root.take_table_or_empty("llm"), env)
    gpu = _gpu_config(root.take_table_or_empty("gpu"))
    nudges = _nudge_config(root.take_table_or_empty("nudges"))
    people = _people_config(root.take_table_or_empty("people"))
    root.finish()
    return StashConfig(data_dir, timezone, llm, gpu, nudges, burst_window_seconds, people)


def _read_toml(path: Path) -> dict[str, object]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as error:
        raise ConfigError(f"cannot read config file {path}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"invalid TOML in config file {path}: {error}") from error


def _data_dir(root: Section, env: Mapping[str, str]) -> Path:
    configured = root.take_optional_text("data_dir")
    if configured is None:
        return _default_data_dir(env)
    return expand_home(configured, env)


def expand_home(raw: str, env: Mapping[str, str]) -> Path:
    if raw == HOME_PREFIX or raw.startswith(f"{HOME_PREFIX}/"):
        return _home(env) / raw[len(HOME_PREFIX) + 1 :]
    return Path(raw)


def _default_data_dir(env: Mapping[str, str]) -> Path:
    xdg_data_home = env.get(XDG_DATA_HOME_VAR, "").strip()
    if xdg_data_home:
        return Path(xdg_data_home) / APP_DIR_NAME
    return _home(env) / DEFAULT_DATA_SUBPATH


def _home(env: Mapping[str, str]) -> Path:
    home = env.get(HOME_VAR, "").strip()
    if not home:
        raise ConfigError(f"{HOME_VAR} is not set, so paths under it cannot be resolved")
    return Path(home)


def _timezone(root: Section) -> ZoneInfo:
    name = root.take_text("timezone", DEFAULT_TIMEZONE)
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ConfigError(f"timezone {name!r} is not a known time zone") from error


def _gpu_config(section: Section) -> GpuConfig:
    defaults = GpuConfig()
    gpu = GpuConfig(
        min_free_vram_mib=section.take_integer("min_free_vram_mib", defaults.min_free_vram_mib),
        max_foreign_utilization_pct=section.take_integer(
            "max_foreign_utilization_pct", defaults.max_foreign_utilization_pct
        ),
        manual_off_hours=section.take_number("manual_off_hours", defaults.manual_off_hours),
        when_unreadable=section.take_choice(
            "when_unreadable", WHEN_UNREADABLE_CHOICES, defaults.when_unreadable
        ),
    )
    section.finish()
    return gpu


def _nudge_config(section: Section) -> NudgeConfig:
    defaults = NudgeConfig()
    nudges = NudgeConfig(
        digest_day=section.take_choice("digest_day", tuple(Weekday), defaults.digest_day),
        digest_time=section.take_time("digest_time", defaults.digest_time),
        reminder_time=section.take_time("reminder_time", defaults.reminder_time),
        followup_time=section.take_time("followup_time", defaults.followup_time),
        forgotten_after_days=section.take_integer(
            "forgotten_after_days", defaults.forgotten_after_days
        ),
        stuck_doing_days=section.take_integer("stuck_doing_days", defaults.stuck_doing_days),
        tick_seconds=section.take_integer("tick_seconds", defaults.tick_seconds),
    )
    section.finish()
    return nudges


def _people_config(section: Section) -> PeopleConfig:
    people = PeopleConfig(lead_days=section.take_integers("lead_days", PeopleConfig().lead_days))
    section.finish()
    return people


def _llm_config(section: Section, env: Mapping[str, str]) -> LlmConfig:
    provider = section.take_required_choice("provider", tuple(ProviderName))
    busy_fallback = section.take_choice("busy_fallback", BUSY_FALLBACKS, "wait")
    providers = _provider_tables(section, env)
    tasks = _per_task(section.take_table_or_empty("tasks"), tuple(ProviderName))
    thinking = _per_task(section.take_table_or_empty("thinking"), tuple(Thinking))
    section.finish()
    return LlmConfig(provider, busy_fallback, providers, tasks, thinking)


def _provider_tables(
    section: Section, env: Mapping[str, str]
) -> dict[ProviderName, ProviderSettings]:
    settings: dict[ProviderName, ProviderSettings] = {}
    for name in ProviderName:
        table = section.take_table(name.value)
        if table is not None:
            settings[name] = _provider_settings(name, table, env)
    return settings


def _provider_settings(
    name: ProviderName, table: Section, env: Mapping[str, str]
) -> ProviderSettings:
    table.forbid("api_key", SECRETS_IN_ENV)
    settings = ProviderSettings(
        name=name,
        base_url=table.take_text("base_url", DEFAULT_BASE_URLS[name]),
        model=table.take_required_text("model"),
        api_key=_api_key(name, env),
        vision_model=table.take_optional_text("vision_model"),
    )
    table.finish()
    return settings


def _api_key(name: ProviderName, env: Mapping[str, str]) -> str | None:
    if name is not ProviderName.OPENROUTER:
        return None
    return env.get(OPENROUTER_API_KEY_VAR, "").strip() or None


def _per_task(section: Section, choices: Sequence[_Choice]) -> dict[LlmTask, _Choice]:
    chosen: dict[LlmTask, _Choice] = {}
    for task in LlmTask:
        choice = section.take_optional_choice(task.value, choices)
        if choice is not None:
            chosen[task] = choice
    section.finish()
    return chosen
