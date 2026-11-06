from pathlib import Path

import pytest
from config_builders import a_nudge_config, a_stash_config

from stash.config import (
    ConfigError,
    GpuConfig,
    StashConfig,
)


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


def test_stash_config_carries_the_nudge_config_it_was_given() -> None:
    # Setup
    nudges = a_nudge_config(tick_seconds=5)

    # Assert
    assert a_stash_config(nudges=nudges).nudges is nudges


def test_stash_config_takes_nudges_right_after_gpu_and_before_the_burst_window() -> None:
    # Setup
    nudges = a_nudge_config(tick_seconds=5)
    base = a_stash_config()

    # Execute
    config = StashConfig(base.data_dir, base.timezone, base.llm, base.gpu, nudges, 4.0)

    # Assert
    assert (config.nudges, config.burst_window_seconds) == (nudges, 4.0)


def test_stash_config_cannot_be_built_without_nudges() -> None:
    # Setup
    base = a_stash_config()

    # Execute / Assert
    with pytest.raises(TypeError, match="nudges"):
        StashConfig(base.data_dir, base.timezone, base.llm, base.gpu)
