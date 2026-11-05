from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any

from stash.hermes_adapter.events import COMMAND_PREFIX, DISPATCH_HOOK, HermesEvent, Verdict
from stash.hermes_adapter.owners import Owners

Handler = Callable[..., Any]


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


class FakeHermesContext:
    def __init__(
        self,
        *,
        owners: Owners,
        config: Mapping[str, Any] | None = None,
        reserved: Collection[str] = (),
    ) -> None:
        self._owners = owners
        self._admitted = _AdmittedChats()
        self._config = dict(config or {})
        self._reserved = frozenset(reserved)
        self.hooks: dict[str, Handler] = {}
        self.platform_handlers: dict[str, Handler] = {}
        self.commands: dict[str, Handler] = {}
        self.command_registrations: list[RegisteredCommand] = []
        self.tools: dict[str, RegisteredTool] = {}
        self.injected: list[InjectedMessage] = []
        self.refused: list[InjectedMessage] = []

    def get_config(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def register_hook(
        self, hook_name: str, callback: Handler, *, hold_stream: bool = False
    ) -> None:
        self.hooks[hook_name] = callback

    def register_platform_handler(self, platform: str, factory: Handler) -> None:
        self.platform_handlers[platform] = factory

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
            self._admitted.admit(event.source.chat_id)
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
        if not self._admitted.admits(origin):
            self.refused.append(message)
            return False
        self.injected.append(message)
        return True
