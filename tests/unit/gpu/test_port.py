from dataclasses import FrozenInstanceError

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


def test_sample_with_utilization_of_exactly_100_is_accepted() -> None:
    # Execute
    sample = a_sample(utilization_pct=100)

    # Assert
    assert sample.utilization_pct == 100


def test_sample_with_all_zero_readings_is_accepted() -> None:
    # Execute
    sample = a_sample(total_mib=0, used_mib=0, utilization_pct=0)

    # Assert
    assert sample == GpuSample(0, 0, 0)


def test_sample_cannot_be_modified() -> None:
    # Setup
    sample = a_sample()

    # Execute / Assert
    with pytest.raises(FrozenInstanceError):
        sample.used_mib = 0  # type: ignore[misc]


def test_foreign_used_subtracts_own_usage_from_used() -> None:
    # Setup
    sample = a_sample(used_mib=10000)

    # Execute
    foreign = sample.foreign_used_mib(own_mib=6000)

    # Assert
    assert foreign == 4000


def test_foreign_used_is_everything_when_own_usage_is_zero() -> None:
    # Setup
    sample = a_sample(used_mib=10000)

    # Execute
    foreign = sample.foreign_used_mib(own_mib=0)

    # Assert
    assert foreign == 10000


def test_foreign_used_is_zero_when_own_usage_equals_used() -> None:
    # Setup
    sample = a_sample(used_mib=6000)

    # Execute
    foreign = sample.foreign_used_mib(own_mib=6000)

    # Assert
    assert foreign == 0


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


def test_free_mib_is_the_total_minus_the_foreign_usage() -> None:
    # Setup
    sample = a_sample(total_mib=10000, used_mib=9000)

    # Execute
    free = sample.free_mib(own_mib=1000)

    # Assert
    assert free == 2000


def test_free_mib_counts_the_whole_gpu_when_nothing_is_foreign() -> None:
    # Setup
    sample = a_sample(total_mib=10000, used_mib=6000)

    # Execute
    free = sample.free_mib(own_mib=6000)

    # Assert
    assert free == 10000


def test_free_mib_with_no_own_usage_is_the_total_minus_the_used() -> None:
    # Setup
    sample = a_sample(total_mib=10000, used_mib=4000)

    # Execute
    free = sample.free_mib(own_mib=0)

    # Assert
    assert free == 6000


def test_free_mib_treats_own_usage_above_used_as_no_foreign_usage() -> None:
    # Setup
    sample = a_sample(total_mib=10000, used_mib=1000)

    # Execute
    free = sample.free_mib(own_mib=5000)

    # Assert
    assert free == 10000


def test_free_mib_with_negative_own_usage_raises_value_error() -> None:
    # Setup
    sample = a_sample()

    # Execute / Assert
    with pytest.raises(ValueError, match="own_mib"):
        sample.free_mib(own_mib=-1)


def test_utilization_exactly_at_the_limit_does_not_exceed_it() -> None:
    # Setup
    sample = a_sample(utilization_pct=50)

    # Execute
    exceeds = sample.utilization_exceeds(50)

    # Assert
    assert exceeds is False


def test_utilization_one_point_above_the_limit_exceeds_it() -> None:
    # Setup
    sample = a_sample(utilization_pct=51)

    # Execute
    exceeds = sample.utilization_exceeds(50)

    # Assert
    assert exceeds is True


def test_utilization_below_the_limit_does_not_exceed_it() -> None:
    # Setup
    sample = a_sample(utilization_pct=49)

    # Execute
    exceeds = sample.utilization_exceeds(50)

    # Assert
    assert exceeds is False


def test_full_utilization_does_not_exceed_a_limit_of_100() -> None:
    # Setup
    sample = a_sample(utilization_pct=100)

    # Execute
    exceeds = sample.utilization_exceeds(100)

    # Assert
    assert exceeds is False


def test_any_utilization_exceeds_a_limit_of_zero_except_idle() -> None:
    # Setup
    sample = a_sample(utilization_pct=1)

    # Execute
    exceeds = sample.utilization_exceeds(0)

    # Assert
    assert exceeds is True


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
