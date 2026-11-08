import httpx

from stash.config import LibraryConfig
from stash.config.library import DEFAULT_BIND
from stash.llm import ProbeResult

PROBE_TIMEOUT = httpx.Timeout(5.0)
LOOPBACK = "127.0.0.1"
HEALTH_PATH = "/healthz"
HEALTH_BODY = "ok"
START_HINT = "start it with stash serve or systemctl --user enable --now stash-serve.service"


class LibraryServerProbe:
    def __init__(self, library: LibraryConfig, client: httpx.Client) -> None:
        self._library = library
        self._client = client

    def check(self) -> ProbeResult:
        port = self._library.port
        try:
            response = self._client.get(self._health_url(), timeout=PROBE_TIMEOUT)
        except httpx.HTTPError:
            return ProbeResult(False, f"not running; {START_HINT}")
        if response.status_code == httpx.codes.OK and response.text == HEALTH_BODY:
            return ProbeResult(True, f"answering on port {port}")
        return ProbeResult(
            False, f"something other than the library server answered on port {port}"
        )

    def _health_url(self) -> str:
        bind = self._library.bind
        host = LOOPBACK if bind == DEFAULT_BIND else bind
        return f"http://{host}:{self._library.port}{HEALTH_PATH}"
