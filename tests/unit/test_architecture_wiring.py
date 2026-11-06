import pytest
from architecture_guard import ADAPTER_MODULES, forbidden_imports_in, project_sources, sources_named

NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
PURE_FEATURE_MODULES = ("stash.doctor", "stash.doctor_probes", "stash.gpu_switch")
LOWER_PACKAGES = [
    "domain",
    "config",
    "llm",
    "gpu",
    "store",
    "enrich",
    "filing",
    "capture",
    "planning",
]
HIGHER_LAYERS = ("stash.app", "stash.rendering", "stash.cli", "stash.hermes_adapter")


def test_the_doctor_and_the_gpu_switch_import_no_network_extractor_or_adapter() -> None:
    # Execute
    offenders = forbidden_imports_in(
        sources_named(*PURE_FEATURE_MODULES),
        (*NETWORK_PROCESS_AND_DATABASE, "yt_dlp", "PIL", "pytesseract", *ADAPTER_MODULES),
    )

    # Assert
    assert offenders == []


def test_the_doctor_and_the_gpu_switch_import_no_entry_point_or_composition_root() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(*PURE_FEATURE_MODULES), HIGHER_LAYERS)

    # Assert
    assert offenders == []


@pytest.mark.parametrize("module", PURE_FEATURE_MODULES)
@pytest.mark.parametrize("package", LOWER_PACKAGES)
def test_no_lower_package_imports_the_doctor_or_the_gpu_switch(package: str, module: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), (module,))

    # Assert
    assert offenders == []


def test_the_capture_package_scans_cover_the_serialisation_wrapper() -> None:
    # Execute
    scanned = project_sources("capture")

    # Assert
    assert "stash.capture.serial" in scanned


def test_the_backup_module_imports_neither_httpx_nor_sqlite3() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named("stash.store.backup"), ("httpx", "sqlite3"))

    # Assert
    assert offenders == []


def test_the_backup_module_is_a_listed_adapter() -> None:
    # Assert
    assert "stash.store.backup" in ADAPTER_MODULES
