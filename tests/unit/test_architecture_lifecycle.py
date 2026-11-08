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
