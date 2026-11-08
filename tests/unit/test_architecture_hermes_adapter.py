import pytest
from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    imported_modules,
    importers_outside,
    is_within,
    project_sources,
)

NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
IMAGING_AND_EXTRACTION = ("yt_dlp", "PIL", "pytesseract")
HERMES_ADAPTER = "stash.hermes_adapter"
CONFIG_LOADER = "stash.config.loader"
COMPOSITION_ROOT = "stash.app"
ASSEMBLY_MODULES = ("stash.hermes_adapter.plugin", "stash.hermes_adapter.wiring")
HERMES_ADAPTER_STASH_PACKAGES = (
    "stash.app",
    "stash.capture",
    "stash.config",
    "stash.domain",
    "stash.gpu",
    "stash.gpu_switch",
    "stash.hermes_adapter",
    "stash.library_html",
    "stash.lifecycle",
    "stash.planning.errors",
    "stash.rendering",
    "stash.store.port",
    "stash.suggestions.results",
)


def hermes_imports_outside_the_allowed_packages(sources: dict[str, str]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if is_within(module, "stash")
        and not any(is_within(module, package) for package in HERMES_ADAPTER_STASH_PACKAGES)
    )


def test_the_hermes_adapter_package_is_scanned_module_by_module() -> None:
    # Execute
    scanned = set(project_sources("hermes_adapter"))

    # Assert
    assert {HERMES_ADAPTER} <= scanned


def test_the_hermes_adapter_package_imports_no_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("hermes_adapter"), ADAPTER_MODULES)

    # Assert
    assert offenders == []


def test_the_hermes_adapter_package_imports_no_network_database_or_imaging_library() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("hermes_adapter"),
        (*NETWORK_PROCESS_AND_DATABASE, *IMAGING_AND_EXTRACTION),
    )

    # Assert
    assert offenders == []


def test_the_hermes_adapter_package_imports_only_the_packages_it_is_allowed_to() -> None:
    # Execute
    offenders = hermes_imports_outside_the_allowed_packages(project_sources("hermes_adapter"))

    # Assert
    assert offenders == []


@pytest.mark.parametrize("target", [COMPOSITION_ROOT, CONFIG_LOADER])
def test_only_the_plugin_and_the_wiring_import_the_composition_root_or_the_config_loader(
    target: str,
) -> None:
    # Execute
    offenders = importers_outside(target, ASSEMBLY_MODULES, project_sources("hermes_adapter"))

    # Assert
    assert offenders == []


def test_nothing_outside_the_hermes_adapter_imports_it() -> None:
    # Execute
    offenders = importers_outside(HERMES_ADAPTER, (HERMES_ADAPTER,), project_sources())

    # Assert
    assert offenders == []


def test_only_the_assembly_modules_and_the_cli_import_the_composition_root() -> None:
    # Execute
    offenders = importers_outside(
        COMPOSITION_ROOT, (COMPOSITION_ROOT, "stash.cli", *ASSEMBLY_MODULES), project_sources()
    )

    # Assert
    assert offenders == []
