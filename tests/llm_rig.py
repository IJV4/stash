import json
from collections.abc import Callable, Sequence
from pathlib import Path

import httpx
from builders import API_KEY, an_ollama_settings, an_openrouter_settings, chat_body
from fakes.gpu import FakeGpuProbe, FakeOwnVram
from fakes.memory_store import MemoryStore

from stash.config import ProviderName, ProviderSettings, StashConfig
from stash.config.loader import load_config
from stash.gpu import GpuGate, GpuProbe, GpuSample
from stash.gpu.probe import NvidiaSmiProbe
from stash.llm import ChatMessage, ChatModel, ModelRouter
from stash.llm.openai_compat import OpenAICompatibleChat
from stash.llm.probes import OllamaControl, OllamaProbe, OpenRouterProbe

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


def missing_nvidia_smi() -> NvidiaSmiProbe:
    def not_installed(args: Sequence[str]) -> str:
        raise FileNotFoundError(args[0])

    return NvidiaSmiProbe(not_installed)


class Rig:
    def __init__(
        self,
        config: StashConfig,
        probe: GpuProbe,
        answer: Answer,
        own_mib: int = 0,
    ) -> None:
        self.requests: list[httpx.Request] = []
        self._config = config
        self._probe = probe
        self._own_mib = own_mib
        self._store = MemoryStore()
        self._client = httpx.Client(transport=httpx.MockTransport(self._record_and(answer)))
        self.gate = self.restarted_gate()
        self.router = ModelRouter(config.llm, self._chat_models(), self.gate)

    def urls(self) -> list[str]:
        return [str(request.url) for request in self.requests]

    def sent_json(self) -> dict[str, object]:
        body: dict[str, object] = json.loads(self.requests[0].content)
        return body

    def restarted_gate(self) -> GpuGate:
        return GpuGate(self._probe, FakeOwnVram(self._own_mib), self._store, self._config.gpu)

    def ollama_probe(self) -> OllamaProbe:
        return OllamaProbe(self._settings(ProviderName.OLLAMA), self._client)

    def ollama_control(self) -> OllamaControl:
        return OllamaControl(self._settings(ProviderName.OLLAMA), self._client)

    def openrouter_probe(self) -> OpenRouterProbe:
        return OpenRouterProbe(self._settings(ProviderName.OPENROUTER), self._client)

    def _settings(self, name: ProviderName) -> ProviderSettings:
        return self._config.llm.providers[name]

    def _record_and(self, answer: Answer) -> Answer:
        def record(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return answer(request)

        return record

    def _chat_models(self) -> dict[ProviderName, ChatModel]:
        return {
            name: OpenAICompatibleChat(settings, self._client)
            for name, settings in self._config.llm.providers.items()
        }


def llm_toml(provider: str, busy_fallback: str = "wait", suggestions: str | None = None) -> str:
    tasks = f'[llm.tasks]\nsuggestions = "{suggestions}"\n' if suggestions else ""
    return (
        f'[llm]\nprovider = "{provider}"\nbusy_fallback = "{busy_fallback}"\n'
        '[llm.ollama]\nmodel = "local-model"\n'
        '[llm.openrouter]\nmodel = "cloud/model"\n'
        f"{tasks}"
    )


def build_rig(
    tmp_path: Path,
    toml: str,
    sample: GpuSample | None,
    answer: Answer = answering_ok,
    probe: GpuProbe | None = None,
    own_mib: int = 0,
) -> Rig:
    path = tmp_path / "stash.toml"
    path.write_text(toml)
    config = load_config(path, {"HOME": str(tmp_path), "OPENROUTER_API_KEY": API_KEY})
    return Rig(config, FakeGpuProbe(sample) if probe is None else probe, answer, own_mib)


def ask(model: ChatModel, schema_name: str = "probe") -> dict[str, object]:
    return model.complete_json([ChatMessage.text("user", "hello")], SCHEMA, schema_name)
