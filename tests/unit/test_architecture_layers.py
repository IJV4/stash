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
)
PURE_GPU_MODULES = ("stash.gpu", "stash.gpu.port", "stash.gpu.override", "stash.gpu.gate")


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
