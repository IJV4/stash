from collections.abc import Callable
from dataclasses import dataclass

SERVING = "serve_forever"
SHUT_DOWN = "shutdown"


@dataclass(frozen=True, slots=True)
class ServerArguments:
    snapshot_source: Callable[[], str]
    token: str
    bind: str
    port: int


class RecordingLibraryServer:
    def __init__(
        self, serving_ends_with: BaseException | None, while_serving: Callable[[], object]
    ) -> None:
        self.events: list[str] = []
        self._serving_ends_with = serving_ends_with
        self._while_serving = while_serving

    def serve_forever(self) -> None:
        self.events.append(SERVING)
        self._while_serving()
        if self._serving_ends_with is not None:
            raise self._serving_ends_with

    def shutdown(self) -> None:
        self.events.append(SHUT_DOWN)


class RecordingLibraryServers:
    def __init__(
        self,
        serving_ends_with: BaseException | None = None,
        bind_failure: OSError | None = None,
        while_serving: Callable[[], object] = lambda: None,
    ) -> None:
        self.created: list[ServerArguments] = []
        self.servers: list[RecordingLibraryServer] = []
        self._serving_ends_with = serving_ends_with
        self._bind_failure = bind_failure
        self._while_serving = while_serving

    def __call__(
        self, snapshot_source: Callable[[], str], token: str, bind: str, port: int
    ) -> RecordingLibraryServer:
        if self._bind_failure is not None:
            raise self._bind_failure
        self.created.append(ServerArguments(snapshot_source, token, bind, port))
        server = RecordingLibraryServer(self._serving_ends_with, self._while_serving)
        self.servers.append(server)
        return server

    @property
    def events(self) -> list[str]:
        return [event for server in self.servers for event in server.events]
