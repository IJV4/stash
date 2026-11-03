from architecture_guard import (
    ADAPTER_MODULES,
    HERMES_MODULES,
    TELEGRAM,
    forbidden_imports_in,
    imported_modules,
    is_within,
    sources_named,
)

RENDERING = "stash.rendering"
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
IMAGING_AND_EXTRACTION = ("yt_dlp", "PIL", "pytesseract")
RENDERING_STASH_PACKAGES = ("stash.capture", "stash.domain", "stash.gpu", "stash.gpu_switch")


def test_the_rendering_module_imports_no_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(RENDERING), ADAPTER_MODULES)

    # Assert
    assert offenders == []


def test_the_rendering_module_imports_no_network_process_database_or_imaging_library() -> None:
    # Execute
    offenders = forbidden_imports_in(
        sources_named(RENDERING), (*NETWORK_PROCESS_AND_DATABASE, *IMAGING_AND_EXTRACTION)
    )

    # Assert
    assert offenders == []


def test_the_rendering_module_imports_neither_telegram_nor_a_hermes_module() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named(RENDERING), (TELEGRAM, *HERMES_MODULES))

    # Assert
    assert offenders == []


def test_the_rendering_module_imports_only_the_packages_it_is_allowed_to() -> None:
    # Execute
    offenders = sorted(
        module
        for module in imported_modules(sources_named(RENDERING)[RENDERING])
        if is_within(module, "stash")
        and not any(is_within(module, package) for package in RENDERING_STASH_PACKAGES)
    )

    # Assert
    assert offenders == []
