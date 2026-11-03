from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass
from typing import Any

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


class FakeHermesContext:
    def __init__(
        self,
        config: Mapping[str, Any] | None = None,
        reserved: Collection[str] = (),
        inject_result: bool = True,
    ) -> None:
        self._config = dict(config or {})
        self._reserved = frozenset(reserved)
        self.inject_result = inject_result
        self.hooks: dict[str, Handler] = {}
        self.platform_handlers: dict[str, Handler] = {}
        self.commands: dict[str, Handler] = {}
        self.command_registrations: list[RegisteredCommand] = []
        self.tools: dict[str, RegisteredTool] = {}
        self.injected: list[InjectedMessage] = []

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

    def inject_message(
        self,
        content: str,
        role: str = "user",
        *,
        session_key: str | None = None,
        origin: Mapping[str, Any] | None = None,
    ) -> bool:
        self.injected.append(InjectedMessage(content, role, session_key, origin))
        return self.inject_result
