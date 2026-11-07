from architecture_guard import (
    ADAPTER_MODULES,
    HERMES_MODULES,
    TELEGRAM,
    forbidden_imports_in,
    imports_outside_allowed,
    project_sources,
)

LIBRARY_HTML = "stash.library_html"
LIBRARY_HTML_MAY_IMPORT = ("stash.domain", LIBRARY_HTML)
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
IMAGING_AND_EXTRACTION = ("yt_dlp", "PIL", "pytesseract")


def test_the_library_html_package_imports_no_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("library_html"), ADAPTER_MODULES)

    # Assert
    assert offenders == []


def test_the_library_html_package_imports_no_network_process_database_or_imaging_library() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("library_html"), (*NETWORK_PROCESS_AND_DATABASE, *IMAGING_AND_EXTRACTION)
    )

    # Assert
    assert offenders == []


def test_the_library_html_package_imports_neither_telegram_nor_a_hermes_module() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("library_html"), (TELEGRAM, *HERMES_MODULES))

    # Assert
    assert offenders == []


def test_the_library_html_package_imports_only_the_standard_library_and_the_domain() -> None:
    # Execute
    offenders = imports_outside_allowed(project_sources("library_html"), LIBRARY_HTML_MAY_IMPORT)

    # Assert
    assert offenders == []
