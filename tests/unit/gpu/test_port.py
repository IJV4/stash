import pytest

from stash.gpu import NoOwnVram
from stash.gpu.port import GpuSample


def a_sample(total_mib: int = 24576, used_mib: int = 4096, utilization_pct: int = 10) -> GpuSample:
    return GpuSample(total_mib, used_mib, utilization_pct)


def test_sample_with_negative_total_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="total_mib"):
        a_sample(total_mib=-1)


def test_sample_with_negative_used_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="used_mib"):
        a_sample(used_mib=-1)


def test_sample_with_negative_utilization_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="utilization_pct"):
        a_sample(utilization_pct=-1)


def test_sample_with_utilization_above_100_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="utilization_pct"):
        a_sample(utilization_pct=101)


def test_foreign_used_is_clamped_to_zero_when_own_usage_exceeds_used() -> None:
    # Setup
    sample = a_sample(used_mib=6000)

    # Execute
    foreign = sample.foreign_used_mib(own_mib=7000)

    # Assert
    assert foreign == 0


def test_foreign_used_with_negative_own_usage_raises_value_error() -> None:
    # Setup
    sample = a_sample()

    # Execute / Assert
    with pytest.raises(ValueError, match="own_mib"):
        sample.foreign_used_mib(own_mib=-1)


def test_free_mib_with_negative_own_usage_raises_value_error() -> None:
    # Setup
    sample = a_sample()

    # Execute / Assert
    with pytest.raises(ValueError, match="own_mib"):
        sample.free_mib(own_mib=-1)


def test_no_own_vram_reports_nothing_held() -> None:
    # Execute
    held = NoOwnVram().own_mib()

    # Assert
    assert held == 0


def test_no_own_vram_leaves_the_whole_foreign_usage_counted() -> None:
    # Setup
    sample = a_sample(used_mib=6000)

    # Execute
    foreign = sample.foreign_used_mib(NoOwnVram().own_mib())

    # Assert
    assert foreign == 6000
