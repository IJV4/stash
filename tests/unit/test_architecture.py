import pytest
from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    imported_modules,
    importers_outside,
    is_storage_free,
    is_within,
    project_sources,
    storage_dependencies_in,
)

ADAPTER_MODULE = "stash.store.sqlite"
ADAPTER_IMPORTERS = ("stash.app",)
SQLITE_USERS = (
    "stash.store.sqlite",
    "stash.store._rows",
    "stash.store._migrate",
    "stash.store._connect",
    "stash.store._transaction",
    "stash.store._item_writes",
    "stash.store._steps",
    "stash.store._people",
    "stash.store._ledger",
    "stash.app.database",
)
ADAPTER_ONLY_IMPORTERS = (
    "stash.store.sqlite",
    "stash.store._item_writes",
    "stash.store._steps",
    "stash.store._people",
    "stash.store._ledger",
)
ROWS_IMPORTERS = (
    "stash.store.sqlite",
    "stash.store._item_writes",
    "stash.store._steps",
    "stash.store._people",
)
SQLITE_STORE_IMPORTERS = ("stash.store.sqlite",)
TRANSACTION_IMPORTERS = (
    "stash.store.sqlite",
    "stash.store._item_writes",
    "stash.store._migrate",
    "stash.store._steps",
    "stash.store._people",
    "stash.store._ledger",
)
LLM_ADAPTERS = tuple(module for module in ADAPTER_MODULES if is_within(module, "stash.llm"))
ENTRY_POINTS = (
    "stash.app",
    "stash.cli",
    "stash.hermes_adapter.plugin",
    "stash.hermes_adapter.wiring",
)
CONFIG_LOADER = "stash.config.loader"


def test_a_plain_import_is_reported_by_its_module_name() -> None:
    # Assert
    assert imported_modules("import sqlite3") == {"sqlite3"}


def test_a_from_import_reports_the_module_and_each_name_as_a_submodule() -> None:
    # Assert
    assert imported_modules("from stash.store import sqlite") == {
        "stash.store",
        "stash.store.sqlite",
    }


def test_a_relative_import_is_rejected() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="relative imports"):
        imported_modules("from . import sqlite")


def test_scanning_a_missing_source_directory_raises_value_error() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="no source files"):
        project_sources("missing")


def test_the_scan_covers_the_domain_and_the_store_port() -> None:
    # Execute
    scanned = set(project_sources())

    # Assert
    assert {"stash.domain.item", "stash.store.port"} <= scanned


@pytest.mark.parametrize(
    ("module", "storage_free"),
    [
        ("sqlite3", False),
        ("os", True),
        ("stash.domain.item", True),
        ("stash.store.sqlite", False),
        ("httpx", False),
    ],
)
def test_a_module_is_storage_free_only_when_it_is_standard_library_or_domain(
    module: str, storage_free: bool
) -> None:
    # Execute / Assert
    assert is_storage_free(module) is storage_free


def test_a_storage_import_is_reported_against_the_module_that_makes_it() -> None:
    # Setup
    sources = {"stash.domain.leaky": "import os\nimport sqlite3\nfrom stash.domain import item"}

    # Execute
    offenders = storage_dependencies_in(sources)

    # Assert
    assert offenders == ["stash.domain.leaky -> sqlite3"]


def test_a_forbidden_import_is_reported_against_the_module_that_makes_it() -> None:
    # Setup
    sources = {"stash.gpu.leaky": "import os\nimport httpx"}

    # Execute
    offenders = forbidden_imports_in(sources, ("httpx",))

    # Assert
    assert offenders == ["stash.gpu.leaky -> httpx"]


def test_an_allowed_import_is_not_reported_as_forbidden() -> None:
    # Setup
    sources = {"stash.gpu.clean": "import os\nfrom stash.gpu import port"}

    # Execute
    offenders = forbidden_imports_in(sources, ("httpx", "stash.gpu.probe"))

    # Assert
    assert offenders == []


def test_a_from_import_of_a_forbidden_submodule_is_reported() -> None:
    # Setup
    sources = {"stash.llm.router": "from stash.gpu import probe"}

    # Execute
    offenders = forbidden_imports_in(sources, ("stash.gpu.probe",))

    # Assert
    assert offenders == ["stash.llm.router -> stash.gpu.probe"]


def test_importing_a_name_from_a_forbidden_package_is_reported_once() -> None:
    # Setup
    sources = {"stash.llm.router": "from httpx import Client, Timeout"}

    # Execute
    offenders = forbidden_imports_in(sources, ("httpx",))

    # Assert
    assert offenders == ["stash.llm.router -> httpx"]


def test_a_module_whose_name_merely_starts_like_a_forbidden_one_is_not_reported() -> None:
    # Setup
    sources = {"stash.gpu.other": "import httpx_extras"}

    # Execute
    offenders = forbidden_imports_in(sources, ("httpx",))

    # Assert
    assert offenders == []


def test_each_forbidden_import_of_a_module_is_reported_in_sorted_order() -> None:
    # Setup
    sources = {"stash.gpu.leaky": "import subprocess\nimport httpx"}

    # Execute
    offenders = forbidden_imports_in(sources, ("subprocess", "httpx"))

    # Assert
    assert offenders == ["stash.gpu.leaky -> httpx", "stash.gpu.leaky -> subprocess"]


def test_an_importer_outside_the_allowed_packages_is_reported() -> None:
    # Setup
    sources = {
        "stash.feature.filing": "import sqlite3",
        "stash.store.sqlite": "import sqlite3",
        "stash.feature.other": "import os",
    }

    # Execute
    offenders = importers_outside("sqlite3", ("stash.store",), sources)

    # Assert
    assert offenders == ["stash.feature.filing"]


def test_domain_modules_have_no_storage_dependencies() -> None:
    # Execute
    offenders = storage_dependencies_in(project_sources("domain"))

    # Assert
    assert offenders == []


def test_the_store_port_has_no_storage_dependencies() -> None:
    # Execute
    offenders = storage_dependencies_in(
        {"stash.store.port": project_sources("store")["stash.store.port"]}
    )

    # Assert
    assert offenders == []


@pytest.mark.parametrize(
    ("target", "allowed"),
    [
        ("sqlite3", SQLITE_USERS),
        ("stash.store._rows", ROWS_IMPORTERS),
        ("stash.store._migrate", SQLITE_STORE_IMPORTERS),
        ("stash.store._connect", SQLITE_STORE_IMPORTERS),
        ("stash.store._item_writes", SQLITE_STORE_IMPORTERS),
        ("stash.store._sql", ADAPTER_ONLY_IMPORTERS),
        ("stash.store._steps", SQLITE_STORE_IMPORTERS),
        ("stash.store._people", SQLITE_STORE_IMPORTERS),
        ("stash.store._ledger", SQLITE_STORE_IMPORTERS),
        ("stash.store._transaction", TRANSACTION_IMPORTERS),
        (ADAPTER_MODULE, ADAPTER_IMPORTERS),
        ("stash.store.backup", ADAPTER_IMPORTERS),
        ("stash.http_client", ADAPTER_IMPORTERS),
        ("stash.llm.openai_compat", ADAPTER_IMPORTERS),
        ("stash.llm.probes", ADAPTER_IMPORTERS),
        ("stash.gpu.probe", ADAPTER_IMPORTERS),
        ("stash.enrich.ytdlp", ADAPTER_IMPORTERS),
        ("stash.enrich.html_meta", ADAPTER_IMPORTERS),
        ("stash.evaluation.tesseract", ADAPTER_IMPORTERS),
        ("stash.library_server", ADAPTER_IMPORTERS),
        ("stash.library_server_probe", ADAPTER_IMPORTERS),
        ("stash.library_access", ("stash.library_server",)),
        ("stash.llm._auth", LLM_ADAPTERS),
        (CONFIG_LOADER, ENTRY_POINTS),
        ("tomllib", (CONFIG_LOADER,)),
        ("stash.config._section", (CONFIG_LOADER,)),
    ],
    ids=[
        "sqlite3",
        "rows",
        "migrate",
        "connect",
        "item-writes",
        "sql",
        "steps",
        "people",
        "ledger",
        "transaction",
        "adapter",
        "store-backup",
        "http-client",
        "llm-openai-compat",
        "llm-probes",
        "gpu-probe",
        "enrich-ytdlp",
        "enrich-html-meta",
        "evaluation-tesseract",
        "library-server",
        "library-server-probe",
        "library-access",
        "llm-auth",
        "config-loader",
        "tomllib",
        "config-section",
    ],
)
def test_a_storage_module_is_imported_only_by_its_allowed_importers(
    target: str, allowed: tuple[str, ...]
) -> None:
    # Execute
    offenders = importers_outside(target, allowed, project_sources())

    # Assert
    assert offenders == []
