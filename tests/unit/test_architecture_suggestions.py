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

SUGGESTIONS = "stash.suggestions"
HERMES_SUGGESTION_MODULES = (
    "stash.hermes_adapter.ports",
    "stash.hermes_adapter.suggest_tools",
    "stash.hermes_adapter.suggest_command",
)
SUGGESTIONS_IMPORTERS = (
    SUGGESTIONS,
    "stash.app.build",
    "stash.app.app",
    *HERMES_SUGGESTION_MODULES,
)
HERMES_MAY_IMPORT_FROM_SUGGESTIONS = ("stash.suggestions.results",)
SUGGESTIONS_MAY_IMPORT = (
    "stash.domain",
    "stash.store.port",
    "stash.llm",
    "stash.config",
    SUGGESTIONS,
)
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
HIGHER_LAYERS = ("stash.app", "stash.rendering", "stash.cli", "stash.hermes_adapter")


def suggestions_imports_beyond_its_results(sources: dict[str, str]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if is_within(module, SUGGESTIONS)
        and not any(is_within(module, shared) for shared in HERMES_MAY_IMPORT_FROM_SUGGESTIONS)
    )


def hermes_modules_that_exist() -> dict[str, str]:
    sources = project_sources("hermes_adapter")
    return {name: sources[name] for name in HERMES_SUGGESTION_MODULES if name in sources}


def test_the_suggestions_package_imports_only_the_standard_library_and_the_layers_below_it() -> (
    None
):
    # Execute
    offenders = imports_outside_allowed(project_sources("suggestions"), SUGGESTIONS_MAY_IMPORT)

    # Assert
    assert offenders == []


def test_the_suggestions_package_imports_no_network_process_database_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("suggestions"), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


def test_the_suggestions_package_imports_no_composition_root_or_entry_point() -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("suggestions"), HIGHER_LAYERS)

    # Assert
    assert offenders == []


@pytest.mark.parametrize(
    "sibling",
    [
        "stash.capture",
        "stash.filing",
        "stash.planning",
        "stash.nudges",
        "stash.lifecycle",
        "stash.people",
    ],
)
def test_suggestions_sits_beside_the_other_features_without_importing_any(sibling: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("suggestions"), (sibling,))

    # Assert
    assert offenders == []


def test_nothing_outside_the_suggestions_package_and_its_listed_importers_imports_it() -> None:
    # Execute
    offenders = importers_outside(SUGGESTIONS, SUGGESTIONS_IMPORTERS, project_sources())

    # Assert
    assert offenders == []


def test_the_hermes_modules_that_use_suggestions_import_nothing_beyond_its_results() -> None:
    # Execute
    offenders = suggestions_imports_beyond_its_results(hermes_modules_that_exist())

    # Assert
    assert offenders == []
