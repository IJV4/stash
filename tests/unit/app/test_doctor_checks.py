from datetime import UTC, datetime

from builders import an_ollama_settings, an_openrouter_settings
from config_builders import a_stash_config, an_llm_config
from fakes.failing_list_store import FailingListStore
from fakes.fake_providers import FakeProviders
from fakes.gpu import FakeGpuProbe
from fakes.memory_store import MemoryStore
from fakes.search_path import FakeSearchPath

from stash.app.doctor_checks import build_doctor
from stash.config import LlmTask, ProviderName, StashConfig
from stash.doctor import DoctorLine
from stash.gpu import GpuProbe, GpuSample
from stash.store import Store

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)
BOTH_PROVIDERS = {
    OLLAMA: an_ollama_settings(),
    OPENROUTER: an_openrouter_settings(),
}


def a_config(**llm_fields: object) -> StashConfig:
    return a_stash_config(llm=an_llm_config(providers=BOTH_PROVIDERS, **llm_fields))


def lines_of(
    config: StashConfig,
    providers: FakeProviders | None = None,
    store: Store | None = None,
    gpu_probe: GpuProbe | None = None,
    executables: dict[str, str] | None = None,
) -> list[DoctorLine]:
    doctor = build_doctor(
        config,
        MemoryStore() if store is None else store,
        (FakeProviders() if providers is None else providers).client(),
        FakeGpuProbe(None) if gpu_probe is None else gpu_probe,
        FakeSearchPath(executables),
        lambda name: object(),
        lambda: NOW,
    )
    return list(doctor.run().lines)


def test_the_checks_run_in_the_documented_order_for_both_providers() -> None:
    # Execute
    lines = lines_of(a_config())

    # Assert
    assert [line.name for line in lines] == [
        "config",
        "database",
        "ollama",
        "openrouter",
        "openrouter model",
        "nvidia-smi",
        "yt-dlp",
        "deno",
        "tesseract",
        "backup",
    ]


def test_only_the_configured_providers_get_a_check() -> None:
    # Setup
    config = a_stash_config()

    # Execute
    lines = lines_of(config)

    # Assert
    assert [line.name for line in lines] == [
        "config",
        "database",
        "ollama",
        "nvidia-smi",
        "yt-dlp",
        "deno",
        "tesseract",
        "backup",
    ]


def required_names(lines: list[DoctorLine]) -> list[str]:
    return [line.name for line in lines if line.required]


def test_the_config_and_database_checks_are_always_required() -> None:
    # Execute
    lines = lines_of(a_config(provider=OPENROUTER))

    # Assert
    assert required_names(lines)[:2] == ["config", "database"]


def test_only_the_provider_in_use_is_required() -> None:
    # Execute
    lines = lines_of(a_config())

    # Assert
    assert required_names(lines) == ["config", "database", "ollama"]


def test_both_openrouter_checks_are_required_when_openrouter_is_the_provider() -> None:
    # Execute
    lines = lines_of(a_config(provider=OPENROUTER))

    # Assert
    assert required_names(lines) == ["config", "database", "openrouter", "openrouter model"]


def test_openrouter_is_required_when_it_is_the_busy_fallback() -> None:
    # Execute
    lines = lines_of(a_config(busy_fallback="openrouter"))

    # Assert
    assert required_names(lines) == [
        "config",
        "database",
        "ollama",
        "openrouter",
        "openrouter model",
    ]


def test_openrouter_is_required_when_a_task_uses_it() -> None:
    # Execute
    lines = lines_of(a_config(tasks={LlmTask.SUGGESTIONS: OPENROUTER}))

    # Assert
    assert "openrouter" in required_names(lines)


def test_the_gpu_tool_checks_are_optional() -> None:
    # Execute
    lines = lines_of(a_config())

    # Assert
    optional = [line.name for line in lines if not line.required]
    assert optional == [
        "openrouter",
        "openrouter model",
        "nvidia-smi",
        "yt-dlp",
        "deno",
        "tesseract",
        "backup",
    ]


def test_the_ollama_check_asks_the_configured_server_for_the_configured_model() -> None:
    # Setup
    providers = FakeProviders()
    providers.ollama_models = ["llama3:8b"]

    # Execute
    lines = lines_of(a_config(), providers)

    # Assert
    assert lines[2].detail == "model llama3:8b is available"


def test_the_openrouter_checks_use_the_configured_key_and_model() -> None:
    # Setup
    providers = FakeProviders()
    providers.openrouter_models = ["cloud/model"]

    # Execute
    lines = lines_of(a_config(), providers)

    # Assert
    assert [line.detail for line in lines[3:5]] == [
        "key is valid; limit remaining: 10",
        "model cloud/model is offered by OpenRouter",
    ]


def test_the_database_check_reports_the_database_path() -> None:
    # Execute
    lines = lines_of(a_config())

    # Assert
    assert lines[1].detail == "ready at /data/stash/stash.db"


def test_the_database_check_fails_when_the_store_cannot_be_read() -> None:
    # Execute
    lines = lines_of(a_config(), store=FailingListStore())

    # Assert
    assert (lines[1].ok, lines[1].detail) == (False, "ListFailed: database is closed")


def test_the_nvidia_smi_check_reads_the_gpu_probe() -> None:
    # Execute
    lines = lines_of(a_config(), gpu_probe=FakeGpuProbe(GpuSample(24576, 1024, 7)))

    # Assert
    assert lines[5].detail == "1024 / 24576 MiB in use, 7% busy"


def test_the_deno_and_tesseract_checks_look_the_tools_up_on_the_path() -> None:
    # Execute
    lines = lines_of(
        a_config(), executables={"deno": "/usr/bin/deno", "tesseract": "/usr/bin/tesseract"}
    )

    # Assert
    assert [line.detail for line in lines[7:9]] == ["/usr/bin/deno", "/usr/bin/tesseract"]


def test_the_yt_dlp_check_asks_whether_the_yt_dlp_module_exists() -> None:
    # Setup
    asked: list[str] = []

    def find_spec(name: str) -> object | None:
        asked.append(name)
        return None

    doctor = build_doctor(
        a_config(),
        MemoryStore(),
        FakeProviders().client(),
        FakeGpuProbe(None),
        FakeSearchPath(),
        find_spec,
        lambda: NOW,
    )

    # Execute
    doctor.run()

    # Assert
    assert asked == ["yt_dlp"]
