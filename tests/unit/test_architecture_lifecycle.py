from architecture_guard import (
    forbidden_imports_in,
    importers_outside,
    imports_outside_allowed,
    project_sources,
)

LIFECYCLE = "stash.lifecycle"
LIFECYCLE_IMPORTERS = (
    LIFECYCLE,
    "stash.capture.ports",
    "stash.capture.completion_buttons",
    "stash.capture.completion_replies",
    "stash.app.build",
    "stash.app.app",
    "stash.rendering",
    "stash.cli.commands",
    "stash.cli.parser",
    "stash.cli.dispatch",
    "stash.hermes_adapter.ports",
    "stash.hermes_adapter.lifecycle_tools",
    "stash.hermes_adapter.lifecycle_schemas",
    "stash.hermes_adapter.tool_json",
    "stash.hermes_adapter.commands",
)
CONCRETE_LIFECYCLE = ("stash.lifecycle.service", "stash.lifecycle.Lifecycle")
LIFECYCLE_MAY_IMPORT = ("stash.domain", "stash.store.port", LIFECYCLE)
ONLY_THE_STORE_PORT = ("stash.store.port",)


def test_an_adapter_module_is_reported_when_only_the_store_port_is_allowed() -> None:
    # Setup
    sources = {"stash.x": "from stash.store import sqlite"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert "stash.x -> stash.store.sqlite" in offenders


def test_the_bare_stash_package_is_reported_even_when_stash_subpackages_are_allowed() -> None:
    # Setup
    sources = {"stash.x": "from stash import lifecycle"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert "stash.x -> stash" in offenders


def test_a_third_party_import_is_reported() -> None:
    # Setup
    sources = {"stash.x": "import httpx"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert offenders == ["stash.x -> httpx"]


def test_a_function_local_third_party_import_is_reported() -> None:
    # Setup
    sources = {"stash.x": "def late():\n    import httpx\n"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert offenders == ["stash.x -> httpx"]


def test_a_standard_library_import_is_not_reported() -> None:
    # Setup
    sources = {"stash.x": "import datetime"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert offenders == []


def test_an_import_from_a_standard_library_submodule_is_not_reported() -> None:
    # Setup
    sources = {"stash.x": "from collections.abc import Callable"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert offenders == []


def test_an_import_from_an_allowed_stash_package_is_not_reported() -> None:
    # Setup
    sources = {"stash.x": "from stash.store.port import UnknownItemError"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert offenders == []


def test_offenders_are_listed_sorted() -> None:
    # Setup
    sources = {"stash.b": "import httpx", "stash.a": "import yaml"}

    # Execute
    offenders = imports_outside_allowed(sources, ONLY_THE_STORE_PORT)

    # Assert
    assert offenders == ["stash.a -> yaml", "stash.b -> httpx"]


def test_the_lifecycle_package_imports_only_the_standard_library_the_domain_and_the_port() -> None:
    # Execute
    offenders = imports_outside_allowed(project_sources("lifecycle"), LIFECYCLE_MAY_IMPORT)

    # Assert
    assert offenders == []


def test_the_lifecycle_scan_covers_the_service_and_the_ports() -> None:
    # Execute
    scanned = project_sources("lifecycle")

    # Assert
    assert {"stash.lifecycle.service", "stash.lifecycle.ports"} <= scanned.keys()


def test_nothing_outside_the_lifecycle_package_imports_it() -> None:
    # Execute
    offenders = importers_outside(LIFECYCLE, LIFECYCLE_IMPORTERS, project_sources())

    # Assert
    assert offenders == []


def test_nothing_in_the_capture_package_imports_the_concrete_lifecycle() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("capture"), CONCRETE_LIFECYCLE)

    # Assert
    assert offenders == []


def test_importing_the_lifecycle_class_from_the_package_is_reported_as_the_concrete_lifecycle() -> (
    None
):
    # Setup
    sources = {"stash.capture.x": "from stash.lifecycle import Lifecycle"}

    # Execute
    offenders = forbidden_imports_in(sources, CONCRETE_LIFECYCLE)

    # Assert
    assert offenders == ["stash.capture.x -> stash.lifecycle.Lifecycle"]


def test_importing_the_lifecycle_service_module_is_reported_as_the_concrete_lifecycle() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.lifecycle.service import Lifecycle"}

    # Execute
    offenders = forbidden_imports_in(sources, CONCRETE_LIFECYCLE)

    # Assert
    assert offenders == ["stash.capture.x -> stash.lifecycle.service"]


def test_importing_only_the_lifecycle_errors_is_not_reported_as_the_concrete_lifecycle() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.lifecycle.errors import UnknownItem"}

    # Execute
    offenders = forbidden_imports_in(sources, CONCRETE_LIFECYCLE)

    # Assert
    assert offenders == []


def test_a_lifecycle_import_from_an_unlisted_module_is_reported_as_an_importer_outside() -> None:
    # Setup
    sources = {"stash.capture.fixes": "from stash.lifecycle.errors import UnknownItem"}

    # Execute
    offenders = importers_outside(LIFECYCLE, LIFECYCLE_IMPORTERS, sources)

    # Assert
    assert offenders == ["stash.capture.fixes"]
