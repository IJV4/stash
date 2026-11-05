from architecture_guard import importers_outside, imports_outside_allowed, project_sources

LIFECYCLE = "stash.lifecycle"
LIFECYCLE_IMPORTERS = (LIFECYCLE,)
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
