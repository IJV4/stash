import asyncio
from collections.abc import Callable

from capture_builders import QUESTION
from fakes.hermes_ctx import FakeHermesContext
from hermes_ctx_builders import a_hermes_context
from hermes_events import CHAT_ID, OWNER_ID, STRANGER_ID, FakeEvent, an_event

from stash.hermes_adapter.assistant import Origin
from stash.hermes_adapter.events import DISPATCH_HOOK, Chat, Verdict
from stash.hermes_adapter.owners import Owners


def answering(ctx: FakeHermesContext, verdict: Verdict) -> FakeHermesContext:
    async def hook(event: FakeEvent) -> dict[str, str]:
        return verdict.hook_result()

    ctx.register_hook(DISPATCH_HOOK, hook)
    return ctx


def a_context_answering(verdict: Verdict) -> FakeHermesContext:
    return answering(a_hermes_context(), verdict)


def inject_into_chat(ctx: FakeHermesContext) -> bool:
    return ctx.inject_message(QUESTION, origin=Origin(Chat(CHAT_ID, OWNER_ID)).as_mapping())


def a_factory_named_alike(calls: list[object]) -> Callable[..., object]:
    def factory(application: object, adapter: object) -> None:
        calls.append(application)

    return factory


def a_differently_named_factory(calls: list[object]) -> Callable[..., object]:
    def other_factory(application: object, adapter: object) -> None:
        calls.append(application)

    return other_factory


def test_an_injection_into_a_chat_with_no_admitted_message_is_refused() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)

    # Execute
    accepted = inject_into_chat(ctx)

    # Assert
    assert (accepted, ctx.injected, len(ctx.refused)) == (False, [], 1)


def test_an_injection_is_accepted_once_the_owner_has_had_a_message_allowed_in_the_chat() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)
    asyncio.run(ctx.dispatch(an_event(chat_id=CHAT_ID)))

    # Execute
    accepted = inject_into_chat(ctx)

    # Assert
    assert (accepted, [message.content for message in ctx.injected]) == (True, [QUESTION])


def test_a_skipped_message_does_not_admit_the_chat() -> None:
    # Setup
    ctx = a_context_answering(Verdict.SKIP)
    asyncio.run(ctx.dispatch(an_event(chat_id=CHAT_ID)))

    # Execute
    accepted = inject_into_chat(ctx)

    # Assert
    assert accepted is False


def test_an_allowed_message_from_somebody_else_does_not_admit_the_chat() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)
    asyncio.run(ctx.dispatch(an_event(chat_id=CHAT_ID, user_id=STRANGER_ID)))

    # Execute
    accepted = inject_into_chat(ctx)

    # Assert
    assert accepted is False


def test_an_admitted_chat_does_not_admit_another_chat() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)
    asyncio.run(ctx.dispatch(an_event(chat_id="9999")))

    # Execute
    accepted = inject_into_chat(ctx)

    # Assert
    assert accepted is False


def test_an_allowed_command_does_not_admit_the_chat() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)
    asyncio.run(ctx.dispatch(an_event(text="/list", chat_id=CHAT_ID)))

    # Execute
    accepted = inject_into_chat(ctx)

    # Assert
    assert accepted is False


def test_connecting_calls_a_registered_platform_factory_with_the_application_and_no_adapter() -> (
    None
):
    # Setup
    ctx = a_hermes_context()
    received: list[tuple[object, object]] = []
    ctx.register_platform_handler(
        "telegram", lambda application, adapter: received.append((application, adapter))
    )
    application = object()

    # Execute
    ctx.connect("telegram", application)

    # Assert
    assert received == [(application, None)]


def test_connecting_calls_the_factory_again_on_every_connection() -> None:
    # Setup
    ctx = a_hermes_context()
    calls: list[object] = []
    ctx.register_platform_handler("telegram", a_factory_named_alike(calls))
    first, second = object(), object()

    # Execute
    ctx.connect("telegram", first)
    ctx.connect("telegram", second)

    # Assert
    assert calls == [first, second]


def test_a_factory_with_the_same_function_name_as_a_registered_one_is_ignored() -> None:
    # Setup
    ctx = a_hermes_context()
    first_calls: list[object] = []
    second_calls: list[object] = []
    ctx.register_platform_handler("telegram", a_factory_named_alike(first_calls))
    ctx.register_platform_handler("telegram", a_factory_named_alike(second_calls))

    # Execute
    ctx.connect("telegram", object())

    # Assert
    assert (len(first_calls), len(second_calls)) == (1, 0)


def test_a_factory_with_a_different_function_name_is_kept_alongside_the_first() -> None:
    # Setup
    ctx = a_hermes_context()
    first_calls: list[object] = []
    second_calls: list[object] = []
    ctx.register_platform_handler("telegram", a_factory_named_alike(first_calls))
    ctx.register_platform_handler("telegram", a_differently_named_factory(second_calls))

    # Execute
    ctx.connect("telegram", object())

    # Assert
    assert (len(first_calls), len(second_calls)) == (1, 1)


def test_connecting_a_platform_does_not_call_the_factories_of_another_platform() -> None:
    # Setup
    ctx = a_hermes_context()
    calls: list[object] = []
    ctx.register_platform_handler("discord", a_factory_named_alike(calls))

    # Execute
    ctx.connect("telegram", object())

    # Assert
    assert calls == []


def test_a_reloaded_context_ignores_a_factory_whose_name_was_registered_before_the_reload() -> None:
    # Setup
    ctx = a_hermes_context()
    before_calls: list[object] = []
    after_calls: list[object] = []
    ctx.register_platform_handler("telegram", a_factory_named_alike(before_calls))
    reloaded = ctx.reloaded()
    reloaded.register_platform_handler("telegram", a_factory_named_alike(after_calls))
    application = object()

    # Execute
    reloaded.connect("telegram", application)

    # Assert
    assert (before_calls, after_calls) == ([application], [])


def test_connecting_through_a_reloaded_context_calls_the_factory_registered_before_the_reload() -> (
    None
):
    # Setup
    ctx = a_hermes_context()
    calls: list[object] = []
    ctx.register_platform_handler("telegram", a_factory_named_alike(calls))
    application = object()

    # Execute
    ctx.reloaded().connect("telegram", application)

    # Assert
    assert calls == [application]


def test_a_chat_admitted_before_the_reload_is_still_admitted_after_it() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)
    asyncio.run(ctx.dispatch(an_event(chat_id=CHAT_ID)))
    reloaded = ctx.reloaded()

    # Execute
    accepted = inject_into_chat(reloaded)

    # Assert
    assert accepted is True


def test_a_reloaded_context_starts_with_no_hooks_of_its_own() -> None:
    # Setup
    ctx = a_context_answering(Verdict.ALLOW)

    # Execute
    reloaded = ctx.reloaded()

    # Assert
    assert reloaded.hooks == {}


def test_a_reloaded_context_with_new_owners_admits_the_new_owners_chat() -> None:
    # Setup
    reloaded = a_hermes_context().reloaded(owners=Owners.parse(STRANGER_ID))
    answering(reloaded, Verdict.ALLOW)
    asyncio.run(reloaded.dispatch(an_event(user_id=STRANGER_ID, chat_id=CHAT_ID)))

    # Execute
    accepted = inject_into_chat(reloaded)

    # Assert
    assert accepted is True
