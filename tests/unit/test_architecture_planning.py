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
)
CAPTURE_MAY_IMPORT_FROM_PLANNING = ("stash.planning.errors", "stash.planning.results")
PLANNING_MAY_IMPORT = (
    "stash.domain",
    "stash.store.port",
    "stash.llm",
    "stash.config",
    PLANNING,
)
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")


def planning_imports_beyond_its_shared_vocabulary(sources: dict[str, str]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if is_within(module, PLANNING)
        and not any(is_within(module, shared) for shared in CAPTURE_MAY_IMPORT_FROM_PLANNING)
    )


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


def test_the_planning_scan_covers_the_service_proposer_parser_prompt_and_schema() -> None:
    # Execute
    scanned = project_sources("planning")

    # Assert
    assert {
        "stash.planning.service",
        "stash.planning.proposer",
        "stash.planning.parse",
        "stash.planning.prompt",
        "stash.planning.schema",
    } <= scanned.keys()


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


def test_importing_the_planning_class_from_the_package_is_reported_as_the_concrete_planning() -> (
    None
):
    # Setup
    sources = {"stash.capture.x": "from stash.planning import Planning"}

    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(sources)

    # Assert
    assert offenders == [
        "stash.capture.x -> stash.planning",
        "stash.capture.x -> stash.planning.Planning",
    ]


def test_importing_the_step_proposer_module_is_reported_as_the_concrete_planning() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.planning.proposer import StepProposer"}

    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(sources)

    # Assert
    assert offenders == [
        "stash.capture.x -> stash.planning.proposer",
        "stash.capture.x -> stash.planning.proposer.StepProposer",
    ]


def test_importing_only_the_planning_errors_is_not_reported_as_the_concrete_planning() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.planning.errors import UnknownItem"}

    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(sources)

    # Assert
    assert offenders == []


def test_importing_only_the_planning_results_is_not_reported_as_the_concrete_planning() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.planning.results import Proposal"}

    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(sources)

    # Assert
    assert offenders == []


@pytest.mark.parametrize("module", ["parse", "ports"])
def test_importing_a_planning_module_beyond_errors_and_results_is_reported(module: str) -> None:
    # Setup
    sources = {"stash.capture.x": f"from stash.planning.{module} import Name"}

    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(sources)

    # Assert
    assert offenders == [
        f"stash.capture.x -> stash.planning.{module}",
        f"stash.capture.x -> stash.planning.{module}.Name",
    ]


def test_a_package_level_planning_import_is_reported_even_for_a_shared_name() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.planning import UnknownItem"}

    # Execute
    offenders = planning_imports_beyond_its_shared_vocabulary(sources)

    # Assert
    assert "stash.capture.x -> stash.planning" in offenders


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


def test_a_planning_import_from_an_unlisted_module_is_reported_as_an_importer_outside() -> None:
    # Setup
    sources = {"stash.capture.fixes": "from stash.planning.errors import UnknownItem"}

    # Execute
    offenders = importers_outside(PLANNING, PLANNING_IMPORTERS, sources)

    # Assert
    assert offenders == ["stash.capture.fixes"]
