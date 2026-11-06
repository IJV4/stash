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

NUDGES = "stash.nudges"
NUDGES_IMPORTERS = (
    NUDGES,
    "stash.capture.nudge_replies",
    "stash.capture.nudge_buttons",
)
CAPTURE_MAY_IMPORT_FROM_NUDGES = ("stash.nudges.due", "stash.nudges.messages")
NUDGES_MAY_IMPORT = ("stash.domain", "stash.store.port", "stash.config.nudges", NUDGES)
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")


def nudges_imports_beyond_what_rendering_needs(sources: dict[str, str]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if is_within(module, NUDGES)
        and not any(is_within(module, shared) for shared in CAPTURE_MAY_IMPORT_FROM_NUDGES)
    )


def test_the_nudges_package_imports_only_the_standard_library_and_the_layers_below_it() -> None:
    # Execute
    offenders = imports_outside_allowed(project_sources("nudges"), NUDGES_MAY_IMPORT)

    # Assert
    assert offenders == []


def test_importing_the_config_loader_is_reported_as_beyond_what_nudges_may_import() -> None:
    # Setup
    sources = {"stash.nudges.x": "from stash.config.loader import load_config"}

    # Execute
    offenders = imports_outside_allowed(sources, NUDGES_MAY_IMPORT)

    # Assert
    assert "stash.nudges.x -> stash.config.loader" in offenders


def test_the_nudges_package_imports_no_network_process_database_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("nudges"), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


def test_the_nudges_scan_covers_the_nudger_schedule_due_types_batching_and_messages() -> None:
    # Execute
    scanned = project_sources("nudges")

    # Assert
    assert {
        "stash.nudges.nudger",
        "stash.nudges.schedule",
        "stash.nudges.due",
        "stash.nudges.batch",
        "stash.nudges.messages",
        "stash.nudges.ports",
    } <= scanned.keys()


def test_nothing_outside_the_nudges_package_and_its_listed_importers_imports_it() -> None:
    # Execute
    offenders = importers_outside(NUDGES, NUDGES_IMPORTERS, project_sources())

    # Assert
    assert offenders == []


def test_capture_imports_no_more_of_nudges_than_the_due_types_and_messages() -> None:
    # Execute
    offenders = nudges_imports_beyond_what_rendering_needs(project_sources("capture"))

    # Assert
    assert offenders == []


@pytest.mark.parametrize("shared", ["due", "messages"])
def test_importing_the_due_types_or_the_messages_is_not_reported_as_more_than_rendering_needs(
    shared: str,
) -> None:
    # Setup
    sources = {"stash.capture.x": f"from stash.nudges.{shared} import Name"}

    # Execute
    offenders = nudges_imports_beyond_what_rendering_needs(sources)

    # Assert
    assert offenders == []


@pytest.mark.parametrize("module", ["nudger", "schedule", "batch", "ports"])
def test_importing_any_other_nudges_module_is_reported_as_more_than_rendering_needs(
    module: str,
) -> None:
    # Setup
    sources = {"stash.capture.x": f"from stash.nudges.{module} import Name"}

    # Execute
    offenders = nudges_imports_beyond_what_rendering_needs(sources)

    # Assert
    assert offenders == [
        f"stash.capture.x -> stash.nudges.{module}",
        f"stash.capture.x -> stash.nudges.{module}.Name",
    ]


def test_a_package_level_nudges_import_is_reported_even_for_a_shared_name() -> None:
    # Setup
    sources = {"stash.capture.x": "from stash.nudges import FollowUp"}

    # Execute
    offenders = nudges_imports_beyond_what_rendering_needs(sources)

    # Assert
    assert "stash.capture.x -> stash.nudges" in offenders


@pytest.mark.parametrize("banned", ["capture", "filing", "planning", "lifecycle"])
def test_nudges_sits_below_capture_and_beside_the_other_features_without_importing_them(
    banned: str,
) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("nudges"), (f"stash.{banned}",))

    # Assert
    assert offenders == []


def test_a_nudges_import_from_an_unlisted_module_is_reported_as_an_importer_outside() -> None:
    # Setup
    sources = {"stash.capture.fixes": "from stash.nudges.due import FollowUp"}

    # Execute
    offenders = importers_outside(NUDGES, NUDGES_IMPORTERS, sources)

    # Assert
    assert offenders == ["stash.capture.fixes"]


def test_a_nudges_import_from_a_listed_rendering_module_is_not_reported() -> None:
    # Setup
    sources = {"stash.capture.nudge_buttons": "from stash.nudges.due import FollowUp"}

    # Execute
    offenders = importers_outside(NUDGES, NUDGES_IMPORTERS, sources)

    # Assert
    assert offenders == []
