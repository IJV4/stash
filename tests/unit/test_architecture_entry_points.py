import pytest
from architecture_guard import forbidden_imports_in, project_sources

HIGHER_LAYERS = ("stash.app", "stash.rendering", "stash.cli", "stash.hermes_adapter")


@pytest.mark.parametrize(
    "package",
    [
        "enrich",
        "filing",
        "llm",
        "gpu",
        "store",
        "config",
        "domain",
        "capture",
        "evaluation",
        "planning",
        "nudges",
        "people",
        "suggestions",
        "delivery",
    ],
)
def test_no_package_imports_the_composition_root_or_an_entry_point(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), HIGHER_LAYERS)

    # Assert
    assert offenders == []
