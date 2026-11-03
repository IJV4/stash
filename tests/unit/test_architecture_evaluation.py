import pytest
from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    imported_modules,
    importers_outside,
    is_within,
    project_sources,
)

TESSERACT_ADAPTER = "stash.evaluation.tesseract"
NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
ALLOWED_STASH_PACKAGES = (
    "stash.domain",
    "stash.config",
    "stash.enrich",
    "stash.filing",
    "stash.llm",
    "stash.evaluation",
)


def pure_evaluation_modules() -> dict[str, str]:
    return {
        name: source
        for name, source in project_sources("evaluation").items()
        if name != TESSERACT_ADAPTER
    }


def test_the_evaluation_package_contains_the_tesseract_adapter() -> None:
    # Execute / Assert
    assert TESSERACT_ADAPTER in project_sources("evaluation")


def test_every_evaluation_module_but_the_tesseract_adapter_imports_no_adapter_or_io_library() -> (
    None
):
    # Execute
    offenders = forbidden_imports_in(
        pure_evaluation_modules(),
        (
            *NETWORK_PROCESS_AND_DATABASE,
            "yt_dlp",
            "PIL",
            "pytesseract",
            *ADAPTER_MODULES,
            "stash.capture",
            "stash.store",
            "stash.gpu",
            "stash.config.loader",
        ),
    )

    # Assert
    assert offenders == []


def test_the_evaluation_package_imports_only_the_packages_beneath_it() -> None:
    # Execute
    offenders = sorted(
        f"{name} -> {module}"
        for name, source in project_sources("evaluation").items()
        for module in imported_modules(source)
        if is_within(module, "stash")
        and not any(is_within(module, package) for package in ALLOWED_STASH_PACKAGES)
    )

    # Assert
    assert offenders == []


def test_the_tesseract_adapter_imports_no_network_or_process_library() -> None:
    # Execute
    offenders = forbidden_imports_in(
        {TESSERACT_ADAPTER: project_sources("evaluation")[TESSERACT_ADAPTER]},
        NETWORK_PROCESS_AND_DATABASE,
    )

    # Assert
    assert offenders == []


@pytest.mark.parametrize("library", ["PIL", "pytesseract"])
def test_only_the_tesseract_adapter_imports_the_imaging_libraries(library: str) -> None:
    # Execute
    offenders = importers_outside(library, (TESSERACT_ADAPTER,), project_sources())

    # Assert
    assert offenders == []


@pytest.mark.parametrize(
    "package", ["domain", "config", "llm", "gpu", "store", "enrich", "filing", "capture"]
)
def test_no_lower_package_imports_the_evaluation_package(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), ("stash.evaluation",))

    # Assert
    assert offenders == []
