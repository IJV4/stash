from collections.abc import Callable
from datetime import datetime

import httpx

from stash.config import ProviderName, StashConfig
from stash.doctor import Doctor, DoctorCheck
from stash.doctor_probes import (
    BackupProbe,
    ConfigProbe,
    DatabaseProbe,
    ExecutableProbe,
    GpuReadingProbe,
    PackageProbe,
    PendingCapturesProbe,
)
from stash.gpu import GpuProbe
from stash.llm import ProviderProbe
from stash.llm.probes import OllamaProbe, OpenRouterModelProbe, OpenRouterProbe
from stash.store import Store

YT_DLP_MODULE = "yt_dlp"
DENO_HINT = "yt-dlp needs a JavaScript runtime for some sites"
TESSERACT_HINT = "needed for the OCR eval arm"


def build_doctor(
    config: StashConfig,
    store: Store,
    client: httpx.Client,
    gpu_probe: GpuProbe,
    which: Callable[[str], str | None],
    find_spec: Callable[[str], object | None],
    clock: Callable[[], datetime],
) -> Doctor:
    return Doctor(
        [
            DoctorCheck.mandatory("config", ConfigProbe(config)),
            DoctorCheck.mandatory("database", DatabaseProbe(store, config.db_path)),
            *_provider_checks(config, client),
            DoctorCheck.optional(
                "nvidia-smi", GpuReadingProbe(gpu_probe, config.gpu.when_unreadable)
            ),
            DoctorCheck.optional("yt-dlp", PackageProbe(YT_DLP_MODULE, find_spec)),
            DoctorCheck.optional("deno", ExecutableProbe("deno", which, DENO_HINT)),
            DoctorCheck.optional("tesseract", ExecutableProbe("tesseract", which, TESSERACT_HINT)),
            DoctorCheck.optional("backup", BackupProbe(store, clock)),
            DoctorCheck.optional("pending captures", PendingCapturesProbe(store)),
        ]
    )


def _provider_checks(config: StashConfig, client: httpx.Client) -> list[DoctorCheck]:
    llm = config.llm
    checks: list[DoctorCheck] = []
    ollama = llm.providers.get(ProviderName.OLLAMA)
    if ollama is not None:
        check = _mandatory_when(llm.uses(ProviderName.OLLAMA))
        checks.append(check("ollama", OllamaProbe(ollama, client)))
    openrouter = llm.providers.get(ProviderName.OPENROUTER)
    if openrouter is not None:
        check = _mandatory_when(llm.uses(ProviderName.OPENROUTER))
        checks.append(check("openrouter", OpenRouterProbe(openrouter, client)))
        checks.append(check("openrouter model", OpenRouterModelProbe(openrouter, client)))
    return checks


def _mandatory_when(used: bool) -> Callable[[str, ProviderProbe], DoctorCheck]:
    return DoctorCheck.mandatory if used else DoctorCheck.optional
