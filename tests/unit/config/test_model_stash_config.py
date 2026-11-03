from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from config_builders import an_llm_config

from stash.config import (
    ConfigError,
    GpuConfig,
    StashConfig,
)


def a_stash_config(**overrides: object) -> StashConfig:
    fields: dict[str, object] = {
        "data_dir": Path("/data/stash"),
        "timezone": ZoneInfo("America/Los_Angeles"),
        "llm": an_llm_config(),
        "gpu": GpuConfig(),
    }
    return StashConfig(**{**fields, **overrides})


def test_gpu_config_defaults() -> None:
    # Setup
    gpu = GpuConfig()

    # Assert
    assert (gpu.min_free_vram_mib, gpu.max_foreign_utilization_pct, gpu.manual_off_hours) == (
        9000,
        30,
        4.0,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_free_vram_mib", -1),
        ("max_foreign_utilization_pct", -1),
        ("max_foreign_utilization_pct", 101),
        ("manual_off_hours", 0.0),
        ("manual_off_hours", -1.0),
        ("manual_off_hours", float("nan")),
    ],
)
def test_gpu_config_out_of_range_value_raises_config_error_naming_the_key(
    field: str, value: float
) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=f"gpu.{field}"):
        GpuConfig(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("min_free_vram_mib", 0),
        ("max_foreign_utilization_pct", 0),
        ("max_foreign_utilization_pct", 100),
        ("manual_off_hours", 0.5),
    ],
)
def test_gpu_config_boundary_values_are_accepted(field: str, value: float) -> None:
    # Execute
    gpu = GpuConfig(**{field: value})

    # Assert
    assert getattr(gpu, field) == value


def test_stash_config_db_path_is_stash_db_inside_data_dir() -> None:
    # Setup
    config = a_stash_config(data_dir=Path("/data/stash"))

    # Assert
    assert config.db_path == Path("/data/stash/stash.db")


def test_stash_config_burst_window_defaults_to_eight_seconds() -> None:
    # Assert
    assert a_stash_config().burst_window_seconds == 8.0


def test_stash_config_with_relative_data_dir_raises_config_error() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="data_dir"):
        a_stash_config(data_dir=Path("relative/stash"))


@pytest.mark.parametrize("burst", [-0.1, float("nan")])
def test_stash_config_with_invalid_burst_window_raises_config_error(burst: float) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match="burst_window_seconds"):
        a_stash_config(burst_window_seconds=burst)


def test_stash_config_accepts_a_zero_burst_window() -> None:
    # Assert
    assert a_stash_config(burst_window_seconds=0.0).burst_window_seconds == 0.0
