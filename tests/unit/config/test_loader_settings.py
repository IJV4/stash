from pathlib import Path
from zoneinfo import ZoneInfo

from config_toml import OLLAMA_TABLE, a_toml, load, load_message

from stash.config import ProviderName


def test_minimal_file_defaults_ollama_base_url(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.llm.providers[ProviderName.OLLAMA].base_url == "http://localhost:11434/v1"


def test_minimal_file_uses_the_configured_ollama_model(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.llm.providers[ProviderName.OLLAMA].model == "m"


def test_minimal_file_defaults_timezone_to_los_angeles(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.timezone == ZoneInfo("America/Los_Angeles")


def test_minimal_file_defaults_busy_fallback_to_wait(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert config.llm.busy_fallback == "wait"


def test_minimal_file_defaults_gpu_limits(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert (config.gpu.min_free_vram_mib, config.gpu.max_foreign_utilization_pct) == (9000, 30)


def test_minimal_file_defaults_manual_off_hours_and_burst_window(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert (config.gpu.manual_off_hours, config.burst_window_seconds) == (4.0, 8.0)


def test_minimal_file_provides_only_the_tables_present(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml())

    # Assert
    assert list(config.llm.providers) == [ProviderName.OLLAMA]


def test_provider_table_accepts_base_url_and_vision_model(tmp_path: Path) -> None:
    # Setup
    tables = '[llm.ollama]\nmodel = "m"\nbase_url = "http://gpu:1/v1"\nvision_model = "v"\n'

    # Execute
    settings = load(tmp_path, a_toml(tables=tables)).llm.providers[ProviderName.OLLAMA]

    # Assert
    assert (settings.base_url, settings.vision_model) == ("http://gpu:1/v1", "v")


def test_gpu_table_overrides_the_limits(tmp_path: Path) -> None:
    # Setup
    gpu = (
        "[gpu]\nmin_free_vram_mib = 1000\nmax_foreign_utilization_pct = 50\nmanual_off_hours = 2\n"
    )

    # Execute
    config = load(tmp_path, a_toml(tables=OLLAMA_TABLE + gpu)).gpu

    # Assert
    assert (config.min_free_vram_mib, config.max_foreign_utilization_pct) == (1000, 50)


def test_integer_manual_off_hours_is_read_as_a_float(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(tables=OLLAMA_TABLE + "[gpu]\nmanual_off_hours = 2\n"))

    # Assert
    assert type(config.gpu.manual_off_hours) is float


def test_out_of_range_gpu_value_is_a_config_error_naming_the_key(tmp_path: Path) -> None:
    # Execute
    message = load_message(
        tmp_path, a_toml(tables=OLLAMA_TABLE + "[gpu]\nmax_foreign_utilization_pct = 101\n")
    )

    # Assert
    assert "gpu.max_foreign_utilization_pct" in message


def test_burst_window_seconds_can_be_configured(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top="burst_window_seconds = 2"))

    # Assert
    assert config.burst_window_seconds == 2.0


def test_timezone_can_be_configured(tmp_path: Path) -> None:
    # Execute
    config = load(tmp_path, a_toml(top='timezone = "Europe/Madrid"'))

    # Assert
    assert config.timezone == ZoneInfo("Europe/Madrid")


def test_unknown_timezone_names_the_key(tmp_path: Path) -> None:
    # Execute
    message = load_message(tmp_path, a_toml(top='timezone = "Mars/Olympus"'))

    # Assert
    assert "timezone" in message


def test_gpu_when_unreadable_defaults_to_busy_and_reads_free(tmp_path: Path) -> None:
    # Execute
    default = load(tmp_path, a_toml(tables=OLLAMA_TABLE))
    free = load(tmp_path, a_toml(tables=OLLAMA_TABLE + '[gpu]\nwhen_unreadable = "free"\n'))

    # Assert
    assert (default.gpu.when_unreadable, free.gpu.when_unreadable) == ("busy", "free")
