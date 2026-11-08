import pytest
from architecture_guard import ADAPTER_MODULES, importers_outside, project_sources

THIRD_PARTY_PACKAGES = ("httpx", "sqlite3", "subprocess", "yt_dlp", "PIL", "pytesseract")
STORE_INTERNALS = (
    "stash.store._rows",
    "stash.store._migrate",
    "stash.store._connect",
    "stash.store._transaction",
    "stash.store._item_writes",
    "stash.store._steps",
    "stash.store._people",
    "stash.store._ledger",
)
ALLOWED_IMPORTERS = (*ADAPTER_MODULES, *STORE_INTERNALS, "stash.app")


@pytest.mark.parametrize("package", THIRD_PARTY_PACKAGES)
def test_a_third_party_package_is_imported_only_by_adapters_and_the_composition_root(
    package: str,
) -> None:
    # Execute
    offenders = importers_outside(package, ALLOWED_IMPORTERS, project_sources())

    # Assert
    assert offenders == []
