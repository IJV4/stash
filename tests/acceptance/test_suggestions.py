import asyncio
import json

import pytest
from app_builders import an_app
from builders import BASE, stored_item
from fakes.memory_store import MemoryStore
from fakes.scripted_chat_model import ScriptedChatModel
from hermes_registration_rig import RegisteredStash, register_stash
from hermes_rig import called
from suggestion_builders import CONTEXT, a_raw_pick, picks_reply
from suggestion_rig import an_engine

from stash.domain import Stage
from stash.llm import LlmDeferred, LlmError, LlmUnavailable
from stash.suggestions import CONTEXT_LIMIT, SuggestionDesk

DUNE, RAMEN, MISO, ZINE, TAXES = "dune", "ramen", "miso", "zine", "taxes"
FOUR_PICKS = picks_reply(
    a_raw_pick(DUNE, "A quiet Saturday read"),
    a_raw_pick(RAMEN, "Close to home"),
    a_raw_pick(MISO, "Two hours is plenty"),
    a_raw_pick(ZINE, "Short and fun"),
)


def want_to_store() -> MemoryStore:
    store = MemoryStore()
    for item_id in (DUNE, RAMEN, MISO, ZINE):
        stored_item(store, id=item_id, title=item_id.title(), stage=Stage.WANT_TO)
    stored_item(store, id=TAXES, title="Taxes", stage=Stage.INBOX)
    return store


def stash_over(store: MemoryStore, model: ScriptedChatModel) -> RegisteredStash:
    desk = SuggestionDesk(store, an_engine(model, lambda: BASE))
    return register_stash(an_app(store=store, suggestions=desk))


def suggest_command(plugin: RegisteredStash, context: str) -> str:
    text: str = asyncio.run(called(plugin.ctx.commands["suggest"], context))
    return text


def test_suggest_answers_at_most_three_bullet_lines_from_the_want_to_items() -> None:
    # Setup
    plugin = stash_over(want_to_store(), ScriptedChatModel([FOUR_PICKS]))

    # Execute
    text = suggest_command(plugin, CONTEXT)

    # Assert
    assert text.splitlines() == [
        "• Dune — A quiet Saturday read",
        "• Ramen — Close to home",
        "• Miso — Two hours is plenty",
    ]


def test_the_suggest_tool_answers_the_same_picks_as_the_command() -> None:
    # Setup
    plugin = stash_over(want_to_store(), ScriptedChatModel([FOUR_PICKS, FOUR_PICKS]))
    lines = suggest_command(plugin, CONTEXT).splitlines()

    # Execute
    answer = json.loads(plugin.ctx.tools["stash_suggest"].handler({"context": CONTEXT}))

    # Assert
    assert [f"• {s['title']} — {s['reason']}" for s in answer["suggestions"]] == lines


def test_with_no_want_to_items_suggest_says_so_and_the_model_is_not_asked() -> None:
    # Setup
    model = ScriptedChatModel([])
    store = MemoryStore()
    stored_item(store, id=TAXES, title="Taxes", stage=Stage.INBOX)
    plugin = stash_over(store, model)

    # Execute
    text = suggest_command(plugin, CONTEXT)

    # Assert
    assert (text, model.calls) == ("Nothing to suggest right now.", [])


@pytest.mark.parametrize("error", [LlmUnavailable("down"), LlmDeferred("gpu busy")])
def test_when_the_model_is_unavailable_or_deferred_suggest_says_so(error: LlmError) -> None:
    # Setup
    plugin = stash_over(want_to_store(), ScriptedChatModel([error]))

    # Execute
    text = suggest_command(plugin, CONTEXT)

    # Assert
    assert text == "Suggestions are unavailable right now."


def test_a_context_over_the_limit_is_refused_by_the_tool_and_the_model_is_not_asked() -> None:
    # Setup
    model = ScriptedChatModel([])
    plugin = stash_over(want_to_store(), model)

    # Execute
    answer = json.loads(
        plugin.ctx.tools["stash_suggest"].handler({"context": "x" * (CONTEXT_LIMIT + 1)})
    )

    # Assert
    assert (answer, model.calls) == (
        {"error": "context must be at most 500 characters"},
        [],
    )
