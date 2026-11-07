import asyncio
from collections.abc import Callable, Collection, Coroutine, Mapping
from dataclasses import dataclass
from typing import Any

from stash.hermes_adapter.events import COMMAND_PREFIX, DISPATCH_HOOK, HermesEvent, Verdict
from stash.hermes_adapter.owners import Owners

Handler = Callable[..., Any]

_PLUGIN_NAME = "stash"


@dataclass(frozen=True, slots=True)
class RegisteredCommand:
    name: str
    handler: Handler
    description: str
    args_hint: str


@dataclass(frozen=True, slots=True)
class RegisteredTool:
    name: str
    toolset: str
    schema: Mapping[str, Any]
    handler: Handler
    description: str


@dataclass(frozen=True, slots=True)
class InjectedMessage:
    content: str
    role: str
    session_key: str | None
    origin: Mapping[str, Any] | None


class _AdmittedChats:
    def __init__(self) -> None:
        self._chat_ids: set[str] = set()

    def admit(self, chat_id: str) -> None:
        self._chat_ids.add(chat_id)

    def admits(self, origin: Mapping[str, Any] | None) -> bool:
        return origin is not None and origin.get("chat_id") in self._chat_ids


class _PlatformFactories:
    def __init__(self) -> None:
        self._by_platform: dict[str, list[Handler]] = {}
        self._keys: set[tuple[str, str]] = set()

    @property
    def by_platform(self) -> dict[str, list[Handler]]:
        return {platform: list(factories) for platform, factories in self._by_platform.items()}

    def register(self, platform: str, factory: Handler) -> None:
        key = (_PLUGIN_NAME, factory.__qualname__)
        if key in self._keys:
            return
        self._keys.add(key)
        self._by_platform.setdefault(platform, []).append(factory)

    def connect(self, platform: str, application: Any) -> None:
        for factory in self._by_platform.get(platform, []):
            factory(application, None)


class _Gateway:
    def __init__(self) -> None:
        self.factories = _PlatformFactories()
        self.admitted = _AdmittedChats()
        self.tasks: list[asyncio.Task[None]] = []


class FakeHermesContext:
    def __init__(
        self,
        *,
        owners: Owners,
        config: Mapping[str, Any] | None = None,
        reserved: Collection[str] = (),
        gateway: _Gateway | None = None,
    ) -> None:
        self._owners = owners
        self._config = dict(config or {})
        self._reserved = frozenset(reserved)
        self._gateway = _Gateway() if gateway is None else gateway
        self.hooks: dict[str, Handler] = {}
        self.commands: dict[str, Handler] = {}
        self.command_registrations: list[RegisteredCommand] = []
        self.tools: dict[str, RegisteredTool] = {}
        self.injected: list[InjectedMessage] = []
        self.refused: list[InjectedMessage] = []

    @property
    def spawned(self) -> list[asyncio.Task[None]]:
        return self._gateway.tasks

    @property
    def platform_handlers(self) -> dict[str, list[Handler]]:
        return self._gateway.factories.by_platform

    def reloaded(self, owners: Owners | None = None) -> "FakeHermesContext":
        return FakeHermesContext(
            owners=self._owners if owners is None else owners,
            config=self._config,
            reserved=self._reserved,
            gateway=self._gateway,
        )

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def register_hook(
        self, hook_name: str, callback: Handler, *, hold_stream: bool = False
    ) -> None:
        self.hooks[hook_name] = callback

    def register_platform_handler(self, platform: str, factory: Handler) -> None:
        self._gateway.factories.register(platform, factory)

    def connect(self, platform: str, application: Any) -> None:
        self._gateway.factories.connect(platform, application)

    def spawn_task(self, coro: Coroutine[Any, Any, None]) -> asyncio.Task[None]:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            coro.close()
            raise
        task = loop.create_task(coro)
        self._gateway.tasks.append(task)
        return task

    async def cancel_spawned(self) -> None:
        for task in self._gateway.tasks:
            task.cancel()
        await asyncio.gather(*self._gateway.tasks, return_exceptions=True)

    def register_command(
        self,
        name: str,
        handler: Handler,
        description: str = "",
        args_hint: str = "",
        argument_mode: str | None = None,
    ) -> RegisteredCommand | None:
        clean = name.lower().strip().lstrip("/")
        if clean in self._reserved:
            return None
        registration = RegisteredCommand(clean, handler, description, args_hint)
        self.commands[clean] = handler
        self.command_registrations.append(registration)
        return registration

    def register_tool(
        self,
        name: str,
        toolset: str,
        schema: Mapping[str, Any],
        handler: Handler,
        check_fn: Callable[[], bool] | None = None,
        requires_env: list[str] | None = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        override: bool = False,
    ) -> RegisteredTool:
        tool = RegisteredTool(name, toolset, schema, handler, description)
        self.tools[name] = tool
        return tool

    async def dispatch(self, event: HermesEvent) -> dict[str, str]:
        verdict: dict[str, str] = await self.hooks[DISPATCH_HOOK](event)
        if verdict == Verdict.ALLOW.hook_result() and self._is_owner_prose(event):
            self._gateway.admitted.admit(event.source.chat_id)
        return verdict

    def _is_owner_prose(self, event: HermesEvent) -> bool:
        user_id = event.source.user_id
        is_owner = user_id is not None and self._owners.admits_user(user_id)
        return is_owner and not (event.text or "").strip().startswith(COMMAND_PREFIX)

    def inject_message(
        self,
        content: str,
        role: str = "user",
        *,
        session_key: str | None = None,
        origin: Mapping[str, Any] | None = None,
    ) -> bool:
        message = InjectedMessage(content, role, session_key, origin)
        if not self._gateway.admitted.admits(origin):
            self.refused.append(message)
            return False
        self.injected.append(message)
        return True
