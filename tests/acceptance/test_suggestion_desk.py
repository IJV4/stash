from builders import BASE, LOS_ANGELES, minutes_after, stored_item
from fakes.model_source import FakeModelSource
from fakes.scripted_chat_model import ScriptedChatModel
from fakes.store_factories import FreshStore
from suggestion_builders import CONTEXT, DUNE_ID, RAMEN_ID, a_raw_pick, picks_reply

from stash.domain import Pick, Stage
from stash.llm import TextPart
from stash.suggestions import Picked, SuggestionDesk, SuggestionEngine
from stash.suggestions.results import SUGGESTION_LIMIT

A_DAY_LATER = minutes_after(24 * 60)
MANY_ITEMS = 60


def a_desk(store: FreshStore, model: ScriptedChatModel) -> SuggestionDesk:
    engine = SuggestionEngine(FakeModelSource(model), lambda: BASE, LOS_ANGELES)
    return SuggestionDesk(store, engine, lambda: A_DAY_LATER)


def test_the_desk_answers_the_want_to_items_the_model_picked_each_with_its_reason() -> None:
    # Setup
    store = FreshStore()
    dune = stored_item(store, id=DUNE_ID, title="Dune", stage=Stage.WANT_TO)
    stored_item(store, id=RAMEN_ID, title="Ramen", stage=Stage.WANT_TO)
    model = ScriptedChatModel([picks_reply(a_raw_pick(DUNE_ID, "A quiet Saturday read"))])

    # Execute
    answer = a_desk(store, model).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Picked((Pick(dune, "A quiet Saturday read"),))


def test_a_model_pick_that_is_not_a_want_to_item_is_dropped() -> None:
    # Setup
    store = FreshStore()
    stored_item(store, id=DUNE_ID, title="Dune", stage=Stage.WANT_TO)
    stored_item(store, id=RAMEN_ID, title="Ramen", stage=Stage.DONE)
    model = ScriptedChatModel([picks_reply(a_raw_pick(RAMEN_ID), a_raw_pick("invented"))])

    # Execute
    answer = a_desk(store, model).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Picked(())


def prompt_of(model: ScriptedChatModel, call: int = 0) -> str:
    return "\n".join(
        part.text
        for message in model.calls[call]
        for part in message.parts
        if isinstance(part, TextPart)
    )


def test_old_want_to_items_are_candidates_even_when_there_are_many_newer_ones() -> None:
    # Setup
    store = FreshStore()
    for number in range(MANY_ITEMS):
        stored_item(
            store,
            id=f"item{number:02}",
            title=f"Title{number:02}x",
            stage=Stage.WANT_TO,
            created_at=minutes_after(number),
            updated_at=minutes_after(number),
        )
    model = ScriptedChatModel([picks_reply()])

    # Execute
    a_desk(store, model).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert "Title00x" in prompt_of(model)
    assert "Title59x" in prompt_of(model)
    assert "Title30x" not in prompt_of(model)


def test_a_short_list_has_no_duplicate_candidates() -> None:
    # Setup
    store = FreshStore()
    for number in range(5):
        stored_item(
            store,
            id=f"item{number}",
            title=f"Title{number}x",
            stage=Stage.WANT_TO,
            created_at=minutes_after(number),
            updated_at=minutes_after(number),
        )
    model = ScriptedChatModel([picks_reply()])

    # Execute
    a_desk(store, model).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    for number in range(5):
        assert prompt_of(model).count(f"Title{number}x") == 1


def test_candidates_are_the_same_on_every_call() -> None:
    # Setup
    store = FreshStore()
    for number in range(MANY_ITEMS):
        stored_item(
            store,
            id=f"item{number:02}",
            title=f"Title{number:02}x",
            stage=Stage.WANT_TO,
            created_at=minutes_after(number),
            updated_at=minutes_after(number),
        )
    model = ScriptedChatModel([picks_reply(), picks_reply()])
    desk = a_desk(store, model)

    # Execute
    desk.suggest(CONTEXT, SUGGESTION_LIMIT)
    desk.suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert prompt_of(model, 0) == prompt_of(model, 1)
