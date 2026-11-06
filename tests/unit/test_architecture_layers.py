import pytest
from architecture_guard import (
    ADAPTER_MODULES,
    forbidden_imports_in,
    importers_outside,
    project_sources,
    sources_named,
)

NETWORK_PROCESS_AND_DATABASE = ("httpx", "subprocess", "sqlite3")
PURE_LLM_MODULES = (
    "stash.llm",
    "stash.llm.port",
    "stash.llm.messages",
    "stash.llm.errors",
    "stash.llm.router",
    "stash.llm.schema",
)
PURE_GPU_MODULES = ("stash.gpu", "stash.gpu.port", "stash.gpu.override", "stash.gpu.gate")
PURE_ENRICH_MODULES = (
    "stash.enrich",
    "stash.enrich.links",
    "stash.enrich.urls",
    "stash.enrich.deadline",
    "stash.enrich.platform_scope",
)


def test_the_adapter_list_names_every_adapter_module_in_the_source_tree() -> None:
    # Execute
    missing = [module for module in ADAPTER_MODULES if module not in project_sources()]

    # Assert
    assert missing == []


def test_the_config_package_imports_no_network_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("config"), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


def test_the_llm_port_messages_errors_and_router_import_no_network_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        sources_named(*PURE_LLM_MODULES), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


def test_the_gpu_port_override_and_gate_import_no_network_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        sources_named(*PURE_GPU_MODULES), (*NETWORK_PROCESS_AND_DATABASE, *ADAPTER_MODULES)
    )

    # Assert
    assert offenders == []


@pytest.mark.parametrize(
    ("package", "forbidden"),
    [
        ("llm", ("stash.gpu",)),
        ("gpu", ("stash.llm",)),
        ("config", ("stash.llm", "stash.gpu")),
        ("domain", ("stash.llm", "stash.gpu", "stash.config")),
    ],
    ids=["llm-not-gpu", "gpu-not-llm", "config-not-llm-or-gpu", "domain-not-above-itself"],
)
def test_a_package_does_not_import_the_packages_that_sit_beside_or_above_it(
    package: str, forbidden: tuple[str, ...]
) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), forbidden)

    # Assert
    assert offenders == []


def test_only_the_gpu_probe_adapter_imports_subprocess_within_the_gpu_package() -> None:
    # Execute
    offenders = importers_outside("subprocess", ("stash.gpu.probe",), project_sources("gpu"))

    # Assert
    assert offenders == []


def test_the_gpu_probe_adapter_does_not_import_httpx() -> None:
    # Execute
    offenders = forbidden_imports_in(sources_named("stash.gpu.probe"), ("httpx",))

    # Assert
    assert offenders == []


def test_the_enrich_package_exports_and_link_model_import_no_network_extractor_or_adapter() -> None:
    # Execute
    offenders = forbidden_imports_in(
        sources_named(*PURE_ENRICH_MODULES),
        (*NETWORK_PROCESS_AND_DATABASE, "yt_dlp", *ADAPTER_MODULES),
    )

    # Assert
    assert offenders == []


def test_only_the_ytdlp_adapter_imports_yt_dlp() -> None:
    # Execute
    offenders = importers_outside("yt_dlp", ("stash.enrich.ytdlp",), project_sources())

    # Assert
    assert offenders == []


def test_only_the_html_meta_adapter_imports_httpx_within_the_enrich_package() -> None:
    # Execute
    offenders = importers_outside("httpx", ("stash.enrich.html_meta",), project_sources("enrich"))

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", ["domain", "config", "llm", "gpu", "store"])
def test_no_lower_package_imports_the_enrich_package(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), ("stash.enrich",))

    # Assert
    assert offenders == []


def test_the_filing_package_imports_no_network_extractor_database_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("filing"),
        (*NETWORK_PROCESS_AND_DATABASE, "yt_dlp", *ADAPTER_MODULES),
    )

    # Assert
    assert offenders == []


@pytest.mark.parametrize("higher", ["stash.capture", "stash.store", "stash.gpu"])
def test_the_filing_package_does_not_import_the_packages_that_sit_beside_or_above_it(
    higher: str,
) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("filing"), (higher,))

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", ["domain", "config", "llm", "gpu", "store", "enrich"])
def test_no_lower_package_imports_the_filing_package(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), ("stash.filing",))

    # Assert
    assert offenders == []


def test_the_capture_package_imports_no_network_extractor_database_or_adapter_module() -> None:
    # Execute
    offenders = forbidden_imports_in(
        project_sources("capture"),
        (*NETWORK_PROCESS_AND_DATABASE, "yt_dlp", *ADAPTER_MODULES),
    )

    # Assert
    assert offenders == []


@pytest.mark.parametrize("forbidden", ["stash.filing", "stash.gpu", "stash.config", "stash.app"])
def test_the_capture_package_does_not_import_the_packages_it_must_not_know(
    forbidden: str,
) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources("capture"), (forbidden,))

    # Assert
    assert offenders == []


@pytest.mark.parametrize("package", ["domain", "config", "llm", "gpu", "store", "enrich", "filing"])
def test_no_lower_package_imports_the_capture_package(package: str) -> None:
    # Execute
    offenders = forbidden_imports_in(project_sources(package), ("stash.capture",))

    # Assert
    assert offenders == []
