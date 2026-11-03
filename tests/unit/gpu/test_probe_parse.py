import pytest

from stash.gpu.port import GpuSample
from stash.gpu.probe import parse_nvidia_smi


def test_parse_reads_total_used_and_utilization_in_that_order() -> None:
    # Execute
    sample = parse_nvidia_smi("12288, 1024, 3")

    # Assert
    assert sample == GpuSample(total_mib=12288, used_mib=1024, utilization_pct=3)


def test_parse_ignores_a_trailing_newline() -> None:
    # Execute
    sample = parse_nvidia_smi("12288, 1024, 3\n")

    # Assert
    assert sample == GpuSample(12288, 1024, 3)


def test_parse_accepts_fields_without_spaces() -> None:
    # Execute
    sample = parse_nvidia_smi("12288,1024,3")

    # Assert
    assert sample == GpuSample(12288, 1024, 3)


def test_parse_skips_leading_blank_lines() -> None:
    # Execute
    sample = parse_nvidia_smi("\n  \n12288, 1024, 3\n")

    # Assert
    assert sample == GpuSample(12288, 1024, 3)


def test_parse_uses_the_first_gpu_when_there_are_several() -> None:
    # Execute
    sample = parse_nvidia_smi("12288, 1024, 3\n24576, 20000, 90\n")

    # Assert
    assert sample == GpuSample(12288, 1024, 3)


def test_parse_of_garbage_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="nvidia-smi"):
        parse_nvidia_smi("NVIDIA-SMI has failed because it couldn't communicate")


def test_parse_of_empty_output_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="no GPU row"):
        parse_nvidia_smi("")


def test_parse_of_whitespace_only_output_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="no GPU row"):
        parse_nvidia_smi(" \n\n")


def test_parse_of_unavailable_readings_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="nvidia-smi"):
        parse_nvidia_smi("[N/A], [N/A], [N/A]")


def test_parse_of_a_row_with_too_few_fields_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="nvidia-smi"):
        parse_nvidia_smi("12288, 1024")


def test_parse_of_a_row_with_too_many_fields_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="nvidia-smi"):
        parse_nvidia_smi("12288, 1024, 3, 7")


def test_parse_of_an_impossible_utilization_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="utilization_pct"):
        parse_nvidia_smi("12288, 1024, 150")
