import pytest
from architecture_guard import forbidden_imports_in, project_sources

ENTRY_POINTS_AND_COMPOSITION_ROOT = ("stash.app", "stash.cli", "stash.hermes_adapter")


@pytest.mark.parametrize(
    "package", ["enrich", "filing", "llm", "gpu", "store", "config", "domain", "capture"]
)
def test_no_package_imports_the_composition_root_or_an_entry_point(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), ENTRY_POINTS_AND_COMPOSITION_ROOT)

    # Assert
    assert offenders == []
