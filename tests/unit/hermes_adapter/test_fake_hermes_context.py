import asyncio

from capture_builders import QUESTION
from fakes.hermes_ctx import FakeHermesContext
from hermes_ctx_builders import a_hermes_context
from hermes_events import CHAT_ID, OWNER_ID, STRANGER_ID, FakeEvent, an_event

from stash.hermes_adapter.assistant import Origin
from stash.hermes_adapter.events import DISPATCH_HOOK, Chat, Verdict


def a_context_answering(verdict: Verdict) -> FakeHermesContext:
    ctx = a_hermes_context()

    async def hook(event: FakeEvent) -> dict[str, str]:
        return verdict.hook_result()

    ctx.register_hook(DISPATCH_HOOK, hook)
    return ctx


def inject_into_chat(ctx: FakeHermesContext) -> bool:
    return ctx.inject_message(QUESTION, origin=Origin(Chat(CHAT_ID, OWNER_ID)).as_mapping())


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
