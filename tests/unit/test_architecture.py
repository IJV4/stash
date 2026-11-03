import ast
import sys
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[2] / "src"
ADAPTER_MODULE = "stash.store.sqlite"
ADAPTER_IMPORTERS = ("stash.app",)
SQLITE_USERS = ("stash.store.sqlite", "stash.store._rows", "stash.store._migrate")
ADAPTER_ONLY_IMPORTERS = ("stash.store.sqlite",)


def module_name(path: Path) -> str:
    parts = list(path.relative_to(SOURCE_ROOT).with_suffix("").parts)
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def imported_modules(source: str) -> set[str]:
    imported: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise ValueError("relative imports are not supported by the architecture guard")
            base = node.module or ""
            imported.update([base, *(f"{base}.{alias.name}" for alias in node.names)])
    return imported


def project_sources(*relative: str) -> dict[str, str]:
    paths = sorted(SOURCE_ROOT.joinpath("stash", *relative).rglob("*.py"))
    if not paths:
        raise ValueError(f"no source files found under {relative or 'stash'}")
    return {module_name(path): path.read_text(encoding="utf-8") for path in paths}


def is_within(module: str, package: str) -> bool:
    return module == package or module.startswith(f"{package}.")


def is_storage_free(module: str) -> bool:
    if is_within(module, "sqlite3"):
        return False
    return module.split(".")[0] in sys.stdlib_module_names or is_within(module, "stash.domain")


def storage_dependencies_in(sources: dict[str, str]) -> list[str]:
    return sorted(
        f"{name} -> {module}"
        for name, source in sources.items()
        for module in imported_modules(source)
        if not is_storage_free(module)
    )


def importers_outside(target: str, allowed: tuple[str, ...], sources: dict[str, str]) -> list[str]:
    return [
        name
        for name, source in sources.items()
        if any(is_within(module, target) for module in imported_modules(source))
        and not any(is_within(name, root) for root in allowed)
    ]


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
        ("stash.store._rows", ADAPTER_ONLY_IMPORTERS),
        ("stash.store._migrate", ADAPTER_ONLY_IMPORTERS),
        (ADAPTER_MODULE, ADAPTER_IMPORTERS),
    ],
    ids=["sqlite3", "rows", "migrate", "adapter"],
)
def test_a_storage_module_is_imported_only_by_its_allowed_importers(
    target: str, allowed: tuple[str, ...]
) -> None:
    # Execute
    offenders = importers_outside(target, allowed, project_sources())

    # Assert
    assert offenders == []
