from datetime import UTC, datetime

from builders import an_ollama_settings, an_openrouter_settings
from config_builders import a_stash_config, an_llm_config
from fakes.fake_providers import FakeProviders
from fakes.gpu import FakeGpuProbe
from fakes.search_path import FakeSearchPath
from fakes.store_factories import FreshStore

from stash.app.doctor_checks import build_doctor
from stash.config import ProviderName, StashConfig
from stash.doctor import DoctorLine
from stash.gpu import GpuProbe
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
        FreshStore() if store is None else store,
        (FakeProviders() if providers is None else providers).client(),
        FakeGpuProbe(None) if gpu_probe is None else gpu_probe,
        FakeSearchPath(executables),
        lambda name: object(),
        lambda: NOW,
    )
    return list(doctor.run().lines)


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
        "library server",
    ]


def test_the_deno_and_tesseract_checks_look_the_tools_up_on_the_path() -> None:
    # Execute
    lines = lines_of(
        a_config(), executables={"deno": "/usr/bin/deno", "tesseract": "/usr/bin/tesseract"}
    )

    # Assert
    assert [line.detail for line in lines[7:9]] == ["/usr/bin/deno", "/usr/bin/tesseract"]
