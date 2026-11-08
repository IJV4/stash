import pytest
from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    imported_modules,
    importers_outside,
    imports_outside_allowed,
    is_within,
    project_sources,
)

PLANNING = "stash.planning"
PLANNING_IMPORTERS = (
    PLANNING,
    "stash.capture.planning_replies",
    "stash.capture.planning_buttons",
    "stash.app.build",
    "stash.app.app",
    "stash.delivery",
    "stash.hermes_adapter.tool_json",
)
CAPTURE_MAY_IMPORT_FROM_PLANNING = ("stash.planning.errors", "stash.planning.results")
HERMES_MAY_IMPORT_FROM_PLANNING = ("stash.planning.errors",)
PLANNING_MAY_IMPORT = (
    "stash.domain",
    "stash.store.port",
    "stash.llm",
    "stash.config",
    PLANNING,
)
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")


def planning_imports_beyond(sources: dict[str, str], shared: tuple[str, ...]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if is_within(module, PLANNING) and not any(is_within(module, allowed) for allowed in shared)
    )


def planning_imports_beyond_its_shared_vocabulary(sources: dict[str, str]) -> list[str]:
    return planning_imports_beyond(sources, CAPTURE_MAY_IMPORT_FROM_PLANNING)


def hermes_imports_beyond_the_planning_errors(sources: dict[str, str]) -> list[str]:
    return planning_imports_beyond(sources, HERMES_MAY_IMPORT_FROM_PLANNING)


def test_the_planning_package_imports_only_the_standard_library_and_the_layers_below_it() -> None:
    # Execute
    offenders = imports_outside_allowed(project_sources("planning"), PLANNING_MAY_IMPORT)

    # Assert
    assert offenders == []


def test_the_planning_package_imports_no_network_process_database_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("planning"), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


def test_nothing_outside_the_planning_package_and_its_listed_importers_imports_it() -> None:
    # Execute
    offenders = importers_outside(PLANNING, PLANNING_IMPORTERS, project_sources())

    # Assert
    assert offenders == []


def test_nothing_in_the_capture_package_imports_the_concrete_planning() -> None:
    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(project_sources("capture"))

    # Assert
    assert offenders == []


@pytest.mark.parametrize(
    ("package", "banned"),
    [("filing", PLANNING), ("planning", "stash.filing"), ("planning", "stash.capture")],
)
def test_planning_sits_beside_filing_and_below_capture_without_importing_either(
    package: str, banned: str
) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), (banned,))

    # Assert
    assert offenders == []


def test_nothing_in_the_hermes_adapter_imports_the_planning_beyond_its_errors() -> None:
    # Execute
    offenders = hermes_imports_beyond_the_planning_errors(project_sources("hermes_adapter"))

    # Assert
    assert offenders == []
