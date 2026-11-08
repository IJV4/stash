from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    importers_outside,
    imports_outside_allowed,
    project_sources,
)

PEOPLE = "stash.people"
PEOPLE_IMPORTERS = (PEOPLE, "stash.app", "stash.cli", "stash.hermes_adapter")
PEOPLE_MAY_IMPORT = ("stash.domain", "stash.store.port", PEOPLE)
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")


def test_the_people_package_imports_only_the_standard_library_and_the_layers_below_it() -> None:
    # Execute
    offenders = imports_outside_allowed(project_sources("people"), PEOPLE_MAY_IMPORT)

    # Assert
    assert offenders == []


def test_the_people_package_imports_no_network_process_database_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("people"), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


def test_only_the_people_package_the_app_and_the_entry_points_import_people() -> None:
    # Execute
    offenders = importers_outside(PEOPLE, PEOPLE_IMPORTERS, project_sources())

    # Assert
    assert offenders == []
