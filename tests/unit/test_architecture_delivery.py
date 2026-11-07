import pytest
from architecture_guard import ADAPTER_MODULES, forbidden_imports_in, project_sources

DELIVERY = "stash.delivery"
LOOP_FORBIDDEN = ("httpx", "subprocess", "sqlite3", "asyncio", "threading", *ADAPTER_MODULES)
ENTRY_POINT_PACKAGES = ["hermes_adapter", "cli"]
LOWER_PACKAGES = [
    "domain",
    "config",
    "llm",
    "gpu",
    "store",
    "enrich",
    "filing",
    "capture",
    "planning",
    "nudges",
    "suggestions",
]


def test_the_delivery_scan_covers_the_nudge_and_proposal_loops() -> None:
    # Execute
    scanned = project_sources("delivery")

    # Assert
    assert {"stash.delivery.nudges", "stash.delivery.proposals"} <= scanned.keys()


def test_the_delivery_loops_import_no_network_process_database_event_loop_or_adapter_module() -> (
    None
):
    # Execute
    offenders = forbidden_imports_in(project_sources("delivery"), LOOP_FORBIDDEN)

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", LOWER_PACKAGES)
def test_no_lower_package_imports_the_delivery_package(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), (DELIVERY,))

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", ENTRY_POINT_PACKAGES)
def test_entry_points_reach_the_delivery_loops_through_the_app_not_by_importing_them(
    package: str,
) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), (DELIVERY,))

    # Assert
    assert offenders == []
