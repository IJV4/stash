import pytest
from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    imported_modules,
    is_within,
    line_count,
    module_level_imports,
    project_sources,
    sources_named,
)

NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
IMAGING_AND_EXTRACTION = ("yt_dlp", "PIL", "pytesseract")
TESSERACT_ADAPTER = "stash.evaluation.tesseract"
ENTRY_POINTS = ("stash.cli", "stash.hermes_adapter")
PACKAGE_VERSION_IMPORT = ("stash", "stash.__version__")
CLI_STASH_PACKAGES = (
    "stash.app",
    "stash.capture",
    "stash.cli",
    "stash.config",
    "stash.doctor",
    "stash.domain",
    "stash.evaluation",
    "stash.gpu",
    "stash.gpu_switch",
    "stash.rendering",
    "stash.store",
)
MAX_MODULE_LINES = 200


def test_a_module_level_import_is_reported() -> None:
    # Execute
    imported = module_level_imports("from stash.evaluation.tesseract import TesseractOcr")

    # Assert
    assert TESSERACT_ADAPTER in imported


def test_an_import_inside_a_function_is_not_a_module_level_import() -> None:
    # Setup
    source = "def make():\n    from stash.evaluation.tesseract import TesseractOcr\n"

    # Execute
    imported = module_level_imports(source)

    # Assert
    assert imported == frozenset()


def test_an_import_guarded_by_a_module_level_condition_is_a_module_level_import() -> None:
    # Setup
    source = "try:\n    import pytesseract\nexcept ImportError:\n    pass\n"

    # Execute
    imported = module_level_imports(source)

    # Assert
    assert "pytesseract" in imported


def test_the_app_package_is_scanned_module_by_module() -> None:
    # Execute
    scanned = set(project_sources("app"))

    # Assert
    assert {"stash.app", "stash.app.build", "stash.app.app"} <= scanned


def test_the_cli_package_is_scanned_module_by_module() -> None:
    # Execute
    scanned = set(project_sources("cli"))

    # Assert
    assert {"stash.cli", "stash.cli.entry", "stash.cli.commands"} <= scanned


def test_no_module_of_the_app_package_imports_the_tesseract_adapter_at_module_level() -> None:
    # Execute
    offenders = sorted(
        name
        for name, source in project_sources("app").items()
        if TESSERACT_ADAPTER in module_level_imports(source)
    )

    # Assert
    assert offenders == []


def test_the_app_package_imports_the_tesseract_adapter_somewhere() -> None:
    # Execute
    importers = [
        name
        for name, source in project_sources("app").items()
        if TESSERACT_ADAPTER in imported_modules(source)
    ]

    # Assert
    assert importers == ["stash.app.ocr"]


def test_no_module_of_the_app_package_imports_the_imaging_libraries_at_module_level() -> None:
    # Execute
    offenders = sorted(
        f"{name} -> {library}"
        for name, source in project_sources("app").items()
        for library in ("PIL", "pytesseract")
        if any(is_within(module, library) for module in module_level_imports(source))
    )

    # Assert
    assert offenders == []


def test_the_cli_package_imports_no_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("cli"), ADAPTER_MODULES)

    # Assert
    assert offenders == []


def test_the_cli_package_imports_no_network_process_database_or_imaging_library() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("cli"), (*NETWORK_PROCESS_AND_DATABASE, *IMAGING_AND_EXTRACTION)
    )

    # Assert
    assert offenders == []


def test_the_cli_package_imports_only_the_packages_it_is_allowed_to() -> None:
    # Execute
    offenders = sorted(
        f"{name} -> {module}"
        for name, source in project_sources("cli").items()
        for module in imported_modules(source)
        if is_within(module, "stash")
        and module not in PACKAGE_VERSION_IMPORT
        and not any(is_within(module, package) for package in CLI_STASH_PACKAGES)
    )

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", ["app", "cli"])
def test_the_app_and_cli_packages_import_no_hermes_adapter(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), ("stash.hermes_adapter",))

    # Assert
    assert offenders == []


def test_the_composition_root_does_not_import_an_entry_point() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("app"), ENTRY_POINTS)

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", ["app", "cli", "hermes_adapter"])
def test_every_module_of_the_app_and_cli_packages_stays_small(package: str) -> None:
    # Execute
    oversized = sorted(
        name
        for name, source in project_sources(package).items()
        if line_count(source) > MAX_MODULE_LINES
    )

    # Assert
    assert oversized == []


def test_the_rendering_module_stays_small() -> None:
    # Execute
    lines = line_count(sources_named("stash.rendering")["stash.rendering"])

    # Assert
    assert lines <= MAX_MODULE_LINES
