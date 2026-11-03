import logging

import httpx

from stash.config import OPENROUTER_API_KEY_VAR, ProviderSettings
from stash.llm._auth import bearer_headers
from stash.llm.errors import LlmUnavailable
from stash.llm.port import ProbeResult

logger = logging.getLogger(__name__)

PROBE_TIMEOUT = httpx.Timeout(5.0)
BYTES_PER_MIB = 1024 * 1024
LATEST_TAG = "latest"
UNEXPECTED_OLLAMA = "unexpected response from Ollama"
UNEXPECTED_OPENROUTER = "unexpected response from OpenRouter"
UNEXPECTED_RESPONSE = "unexpected response"
MALFORMED_BODY = (ValueError, RecursionError, KeyError, TypeError)


class _OllamaServer:
    def __init__(self, settings: ProviderSettings, client: httpx.Client) -> None:
        self._settings = settings
        self._client = client

    def get(self, path: str) -> httpx.Response:
        return self._client.get(self._settings.native_endpoint(path), timeout=PROBE_TIMEOUT)

    def post(self, path: str, payload: dict[str, object]) -> httpx.Response:
        return self._client.post(
            self._settings.native_endpoint(path), json=payload, timeout=PROBE_TIMEOUT
        )

    def unreachable(self) -> str:
        return f"cannot reach Ollama at {self._settings.root_url}"

    def refused(self, response: httpx.Response) -> str:
        return f"Ollama at {self._settings.root_url} answered HTTP {response.status_code}"


def _listed_model_names(response: httpx.Response) -> list[str] | None:
    try:
        names = [entry["name"] for entry in response.json()["models"]]
    except MALFORMED_BODY:
        return None
    return names if all(isinstance(name, str) for name in names) else None


def _is_listed(model: str, names: list[str]) -> bool:
    return model in names or (":" not in model and f"{model}:{LATEST_TAG}" in names)


class OllamaProbe:
    def __init__(self, settings: ProviderSettings, client: httpx.Client) -> None:
        self._model = settings.model
        self._ollama = _OllamaServer(settings, client)

    def check(self) -> ProbeResult:
        try:
            response = self._ollama.get("api/tags")
        except httpx.RequestError:
            return ProbeResult(False, self._ollama.unreachable())
        if not response.is_success:
            return ProbeResult(False, self._ollama.refused(response))
        names = _listed_model_names(response)
        if names is None:
            return ProbeResult(False, UNEXPECTED_OLLAMA)
        return self._verdict(names)

    def _verdict(self, names: list[str]) -> ProbeResult:
        if _is_listed(self._model, names):
            return ProbeResult(True, f"model {self._model} is available")
        return ProbeResult(False, f"model {self._model} is not pulled (ollama pull {self._model})")


class OllamaControl:
    def __init__(self, settings: ProviderSettings, client: httpx.Client) -> None:
        self._model = settings.model
        self._ollama = _OllamaServer(settings, client)

    def unload(self) -> None:
        try:
            response = self._ollama.post("api/generate", {"model": self._model, "keep_alive": 0})
        except httpx.RequestError as error:
            raise LlmUnavailable(self._ollama.unreachable()) from error
        if not response.is_success:
            raise LlmUnavailable(self._ollama.refused(response))


def _vram_bytes(entry: dict[str, object]) -> int:
    size = entry["size_vram"]
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise ValueError("size_vram must be a non-negative integer")
    return size


def _loaded_mib(response: httpx.Response) -> int | None:
    try:
        total = sum(_vram_bytes(entry) for entry in response.json()["models"])
    except MALFORMED_BODY:
        return None
    return total // BYTES_PER_MIB


class OllamaVramUsage:
    def __init__(self, settings: ProviderSettings, client: httpx.Client) -> None:
        self._ollama = _OllamaServer(settings, client)

    def own_mib(self) -> int:
        try:
            response = self._ollama.get("api/ps")
        except httpx.RequestError as error:
            return self._assume_none(type(error).__name__)
        if not response.is_success:
            return self._assume_none(f"HTTP {response.status_code}")
        loaded = _loaded_mib(response)
        return self._assume_none(UNEXPECTED_RESPONSE) if loaded is None else loaded

    @staticmethod
    def _assume_none(cause: str) -> int:
        logger.warning("Ollama VRAM usage unavailable: %s", cause)
        return 0


def _remaining_limit(response: httpx.Response) -> str | None:
    try:
        remaining = response.json()["data"]["limit_remaining"]
    except MALFORMED_BODY:
        return None
    if remaining is None:
        return "unlimited"
    if isinstance(remaining, int | float) and not isinstance(remaining, bool):
        return str(remaining)
    return None


class OpenRouterProbe:
    def __init__(self, settings: ProviderSettings, client: httpx.Client) -> None:
        self._base_url = settings.base_url
        self._url = settings.endpoint("key")
        self._has_key = bool(settings.api_key)
        self._headers = bearer_headers(settings)
        self._client = client

    def check(self) -> ProbeResult:
        if not self._has_key:
            return ProbeResult(False, f"{OPENROUTER_API_KEY_VAR} is not set")
        try:
            response = self._client.get(self._url, headers=self._headers, timeout=PROBE_TIMEOUT)
        except httpx.RequestError:
            return ProbeResult(False, f"cannot reach OpenRouter at {self._base_url}")
        return self._verdict(response)

    @staticmethod
    def _verdict(response: httpx.Response) -> ProbeResult:
        if response.status_code == httpx.codes.UNAUTHORIZED:
            return ProbeResult(False, "invalid key")
        if not response.is_success:
            return ProbeResult(False, f"OpenRouter answered HTTP {response.status_code}")
        remaining = _remaining_limit(response)
        if remaining is None:
            return ProbeResult(False, UNEXPECTED_OPENROUTER)
        return ProbeResult(True, f"key is valid; limit remaining: {remaining}")
