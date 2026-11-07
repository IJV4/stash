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


def test_the_suggestions_scan_covers_the_desk_engine_parser_prompt_and_schema() -> None:
    # Execute
    scanned = project_sources("suggestions")

    # Assert
    assert {
        "stash.suggestions.desk",
        "stash.suggestions.engine",
        "stash.suggestions.parse",
        "stash.suggestions.prompt",
        "stash.suggestions.schema",
    } <= scanned.keys()


def test_nothing_outside_the_suggestions_package_and_its_listed_importers_imports_it() -> None:
    # Execute
    offenders = importers_outside(SUGGESTIONS, SUGGESTIONS_IMPORTERS, project_sources())

    # Assert
    assert offenders == []


@pytest.mark.parametrize(
    "module",
    [
        "stash.nudges.digest_builder",
        "stash.capture.pick_lines",
        "stash.hermes_adapter.wiring",
        "stash.planning.service",
    ],
)
def test_a_suggestions_import_from_an_unlisted_module_is_reported_as_an_importer_outside(
    module: str,
) -> None:
    # Setup
    sources = {module: "from stash.suggestions.results import Picked"}

    # Execute
    offenders = importers_outside(SUGGESTIONS, SUGGESTIONS_IMPORTERS, sources)

    # Assert
    assert offenders == [module]


def test_a_suggestions_import_from_a_listed_hermes_module_is_not_reported() -> None:
    # Setup
    sources = {"stash.hermes_adapter.suggest_tools": "from stash.suggestions.results import Picked"}

    # Execute
    offenders = importers_outside(SUGGESTIONS, SUGGESTIONS_IMPORTERS, sources)

    # Assert
    assert offenders == []


def test_the_hermes_modules_that_use_suggestions_import_nothing_beyond_its_results() -> None:
    # Execute
    offenders = suggestions_imports_beyond_its_results(hermes_modules_that_exist())

    # Assert
    assert offenders == []


def test_importing_only_the_suggestions_results_is_not_reported() -> None:
    # Setup
    sources = {"stash.hermes_adapter.x": "from stash.suggestions.results import Picked"}

    # Execute
    offenders = suggestions_imports_beyond_its_results(sources)

    # Assert
    assert offenders == []


def test_importing_the_desk_module_is_reported_as_beyond_the_results() -> None:
    # Setup
    sources = {"stash.hermes_adapter.x": "from stash.suggestions.desk import SuggestionDesk"}

    # Execute
    offenders = suggestions_imports_beyond_its_results(sources)

    # Assert
    assert offenders == [
        "stash.hermes_adapter.x -> stash.suggestions.desk",
        "stash.hermes_adapter.x -> stash.suggestions.desk.SuggestionDesk",
    ]


def test_a_package_level_suggestions_import_is_reported_even_for_a_shared_name() -> None:
    # Setup
    sources = {"stash.hermes_adapter.x": "from stash.suggestions import Picked"}

    # Execute
    offenders = suggestions_imports_beyond_its_results(sources)

    # Assert
    assert "stash.hermes_adapter.x -> stash.suggestions" in offenders
