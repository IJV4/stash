import json
from collections.abc import Callable, Sequence
from pathlib import Path

import httpx
from builders import API_KEY, BASE, an_ollama_settings, an_openrouter_settings, chat_body

from stash.app import StashApp, build_app
from stash.config import ProviderName, ProviderSettings, StashConfig
from stash.config.loader import load_config
from stash.gpu import GpuGate, GpuSample
from stash.gpu.probe import CommandRunner
from stash.llm import ChatMessage, ChatModel
from stash.llm.probes import OllamaControl, OllamaProbe, OpenRouterProbe

OLLAMA_PS_PATH = "/api/ps"
BYTES_PER_MIB = 1024 * 1024
OLLAMA_ROOT = "http://localhost:11434"
OLLAMA_URL = an_ollama_settings().endpoint("chat/completions")
OPENROUTER_URL = an_openrouter_settings().endpoint("chat/completions")
SCHEMA = {"type": "object", "properties": {"ok": {"type": "boolean"}}}
FREE_GPU = GpuSample(total_mib=24576, used_mib=1024, utilization_pct=2)
BUSY_GPU = GpuSample(total_mib=24576, used_mib=20000, utilization_pct=5)
HOT_GPU = GpuSample(total_mib=24576, used_mib=1024, utilization_pct=95)

Answer = Callable[[httpx.Request], httpx.Response]


def replying(status: int, body: object) -> Answer:
    return lambda request: httpx.Response(status, json=body)


def answering_ok(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json=chat_body('{"ok": true}'))


def missing_nvidia_smi() -> CommandRunner:
    def not_installed(args: Sequence[str]) -> str:
        raise FileNotFoundError(args[0])

    return not_installed


def smi_reporting(sample: GpuSample) -> CommandRunner:
    row = f"{sample.total_mib}, {sample.used_mib}, {sample.utilization_pct}\n"
    return lambda args: row


def _nothing_installed(name: str) -> str | None:
    return None


class Rig:
    def __init__(
        self,
        config: StashConfig,
        run: CommandRunner,
        answer: Answer,
        own_mib: int = 0,
    ) -> None:
        self.requests: list[httpx.Request] = []
        self._config = config
        self._run = run
        self._own_mib = own_mib
        self._client = httpx.Client(transport=httpx.MockTransport(self._record_and(answer)))
        app = self._build_app()
        self.gate = app.gpu
        self.router = app.router

    def urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]

    def sent_json(self) -> dict[str, object]:
        body: dict[str, object] = json.loads(self.requests[0].content)
        return body

    def restarted_gate(self) -> GpuGate:
        return self._build_app().gpu

    def ollama_probe(self) -> OllamaProbe:
        return OllamaProbe(self._settings(ProviderName.OLLAMA), self._client)

    def ollama_control(self) -> OllamaControl:
        return OllamaControl(self._settings(ProviderName.OLLAMA), self._client)

    def openrouter_probe(self) -> OpenRouterProbe:
        return OpenRouterProbe(self._settings(ProviderName.OPENROUTER), self._client)

    def _build_app(self) -> StashApp:
        return build_app(
            self._config,
            client=self._client,
            run=self._run,
            which=_nothing_installed,
            clock=lambda: BASE,
        )

    def _settings(self, name: ProviderName) -> ProviderSettings:
        return self._config.llm.providers[name]

    def _record_and(self, answer: Answer) -> Answer:
        def record(request: httpx.Request) -> httpx.Response:
            if request.url.path == OLLAMA_PS_PATH:
                return httpx.Response(200, json=self._loaded_models())
            self.requests.append(request)
            return answer(request)

        return record

    def _loaded_models(self) -> dict[str, object]:
        return {"models": [{"size_vram": self._own_mib * BYTES_PER_MIB}]}


def llm_toml(
    provider: str,
    busy_fallback: str = "wait",
    suggestions: str | None = None,
    filing_thinking: str | None = None,
    vision_model: str | None = None,
) -> str:
    tasks = f'[llm.tasks]\nsuggestions = "{suggestions}"\n' if suggestions else ""
    thinking = f'[llm.thinking]\nfiling = "{filing_thinking}"\n' if filing_thinking else ""
    vision = f'vision_model = "{vision_model}"\n' if vision_model else ""
    return (
        f'[llm]\nprovider = "{provider}"\nbusy_fallback = "{busy_fallback}"\n'
        f'[llm.ollama]\nmodel = "local-model"\n{vision}'
        '[llm.openrouter]\nmodel = "cloud/model"\n'
        f"{tasks}"
        f"{thinking}"
    )


def build_rig(
    tmp_path: Path,
    toml: str,
    sample: GpuSample | None,
    answer: Answer = answering_ok,
    run: CommandRunner | None = None,
    own_mib: int = 0,
) -> Rig:
    path = tmp_path / "stash.toml"
    path.write_text(f'data_dir = "{tmp_path / "data"}"\n{toml}')
    config = load_config(path, {"HOME": str(tmp_path), "OPENROUTER_API_KEY": API_KEY})
    if run is None:
        run = missing_nvidia_smi() if sample is None else smi_reporting(sample)
    return Rig(config, run, answer, own_mib)


def ask(model: ChatModel, schema_name: str = "probe") -> dict[str, object]:
    return model.complete_json([ChatMessage.text("user", "hello")], SCHEMA, schema_name)
