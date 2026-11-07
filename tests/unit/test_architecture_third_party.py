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


@pytest.mark.parametrize(
    ("package", "source"),
    [
        ("httpx", "import httpx"),
        ("sqlite3", "import sqlite3"),
        ("subprocess", "from subprocess import run"),
        ("yt_dlp", "import yt_dlp"),
        ("PIL", "from PIL import Image"),
        ("pytesseract", "import pytesseract"),
    ],
    ids=THIRD_PARTY_PACKAGES,
)
def test_a_feature_module_importing_a_third_party_package_is_reported(
    package: str, source: str
) -> None:
    # Setup
    sources = {"stash.enrich.leaky": source}

    # Execute
    offenders = importers_outside(package, ALLOWED_IMPORTERS, sources)

    # Assert
    assert offenders == ["stash.enrich.leaky"]


def test_the_composition_root_importing_a_third_party_package_is_not_reported() -> None:
    # Setup
    sources = {"stash.app.build": "import httpx"}

    # Execute
    offenders = importers_outside("httpx", ALLOWED_IMPORTERS, sources)

    # Assert
    assert offenders == []


def test_an_adapter_importing_its_third_party_package_is_not_reported() -> None:
    # Setup
    sources = {"stash.gpu.probe": "import subprocess"}

    # Execute
    offenders = importers_outside("subprocess", ALLOWED_IMPORTERS, sources)

    # Assert
    assert offenders == []
