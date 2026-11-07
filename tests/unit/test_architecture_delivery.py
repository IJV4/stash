from architecture_guard import ADAPTER_MODULES, forbidden_imports_in, project_sources

DELIVERY = "stash.delivery"
LOOP_FORBIDDEN = ("httpx", "subprocess", "sqlite3", "asyncio", "threading", *ADAPTER_MODULES)
PACKAGES_THAT_DO_NOT_IMPORT_DELIVERY = [
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
    "people",
    "suggestions",
    "hermes_adapter",
    "cli",
]


def test_the_delivery_loops_import_no_network_process_database_event_loop_or_adapter_module() -> (
    None
):
    # Execute
    offenders = forbidden_imports_in(project_sources("delivery"), LOOP_FORBIDDEN)

    # Assert
    assert offenders == []


def test_only_the_app_imports_the_delivery_package() -> None:
    # Execute
    offenders = [
        offender
        for package in PACKAGES_THAT_DO_NOT_IMPORT_DELIVERY
        for offender in forbidden_imports_in(project_sources(package), (DELIVERY,))
    ]

    # Assert
    assert offenders == []
