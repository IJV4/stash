from pathlib import Path

import pytest
from config_builders import a_stash_config
from fakes.failing_list_store import FailingListStore, ListFailed
from fakes.gpu import FakeGpuProbe
from fakes.memory_store import MemoryStore
from fakes.search_path import FakeSearchPath

from stash.doctor_probes import (
    ConfigProbe,
    DatabaseProbe,
    ExecutableProbe,
    GpuReadingProbe,
    PackageProbe,
)
from stash.gpu import GpuSample
from stash.llm import ProbeResult


def test_the_config_probe_always_passes_and_names_the_provider_and_data_directory() -> None:
    # Setup
    probe = ConfigProbe(a_stash_config(data_dir=Path("/data/stash")))

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(True, "provider ollama, data directory /data/stash")


def test_the_database_probe_passes_when_the_store_can_list_items() -> None:
    # Setup
    probe = DatabaseProbe(MemoryStore(), Path("/data/stash/stash.db"))

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(True, "ready at /data/stash/stash.db")


def test_the_database_probe_lets_a_store_failure_surface() -> None:
    # Setup
    probe = DatabaseProbe(FailingListStore(), Path("/data/stash/stash.db"))

    # Execute / Assert
    with pytest.raises(ListFailed):
        probe.check()


def test_the_nvidia_smi_probe_reports_the_memory_in_use_and_the_utilisation() -> None:
    # Setup
    probe = GpuReadingProbe(FakeGpuProbe(GpuSample(24576, 1024, 7)))

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(True, "1024 / 24576 MiB in use, 7% busy")


def test_the_nvidia_smi_probe_fails_when_there_is_no_gpu_reading() -> None:
    # Setup
    probe = GpuReadingProbe(FakeGpuProbe(None))

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(False, "no NVIDIA GPU found (nvidia-smi missing or failed)")


def test_the_package_probe_passes_when_the_module_can_be_found() -> None:
    # Setup
    probe = PackageProbe("yt_dlp", lambda name: object())

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(True, "installed")


def test_the_package_probe_asks_for_the_module_by_name() -> None:
    # Setup
    asked: list[str] = []

    def find_spec(name: str) -> object | None:
        asked.append(name)
        return None

    # Execute
    PackageProbe("yt_dlp", find_spec).check()

    # Assert
    assert asked == ["yt_dlp"]


def test_the_package_probe_fails_when_the_module_is_missing() -> None:
    # Setup
    probe = PackageProbe("yt_dlp", lambda name: None)

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(False, "not installed")


def test_the_executable_probe_passes_with_the_path_where_it_was_found() -> None:
    # Setup
    probe = ExecutableProbe("deno", FakeSearchPath({"deno": "/usr/bin/deno"}), "a hint")

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(True, "/usr/bin/deno")


def test_the_executable_probe_fails_with_its_hint_when_the_tool_is_not_on_the_path() -> None:
    # Setup
    probe = ExecutableProbe("deno", FakeSearchPath(), "yt-dlp needs a JavaScript runtime")

    # Execute
    result = probe.check()

    # Assert
    assert result == ProbeResult(False, "not found on PATH (yt-dlp needs a JavaScript runtime)")
