from builders import BASE, LOS_ANGELES, stored_item
from fakes.memory_store import MemoryStore
from fakes.model_source import FakeModelSource
from fakes.scripted_chat_model import ScriptedChatModel
from suggestion_builders import CONTEXT, DUNE_ID, RAMEN_ID, a_raw_pick, picks_reply

from stash.domain import Pick, Stage
from stash.suggestions import Picked, SuggestionDesk, SuggestionEngine
from stash.suggestions.results import SUGGESTION_LIMIT


def a_desk(store: MemoryStore, model: ScriptedChatModel) -> SuggestionDesk:
    engine = SuggestionEngine(FakeModelSource(model), lambda: BASE, LOS_ANGELES)
    return SuggestionDesk(store, engine)


def test_the_desk_answers_the_want_to_items_the_model_picked_each_with_its_reason() -> None:
    # Setup
    store = MemoryStore()
    dune = stored_item(store, id=DUNE_ID, title="Dune", stage=Stage.WANT_TO)
    stored_item(store, id=RAMEN_ID, title="Ramen", stage=Stage.WANT_TO)
    model = ScriptedChatModel([picks_reply(a_raw_pick(DUNE_ID, "A quiet Saturday read"))])

    # Execute
    answer = a_desk(store, model).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Picked((Pick(dune, "A quiet Saturday read"),))


def test_a_model_pick_that_is_not_a_want_to_item_is_dropped() -> None:
    # Setup
    store = MemoryStore()
    stored_item(store, id=DUNE_ID, title="Dune", stage=Stage.WANT_TO)
    stored_item(store, id=RAMEN_ID, title="Ramen", stage=Stage.DONE)
    model = ScriptedChatModel([picks_reply(a_raw_pick(RAMEN_ID), a_raw_pick("invented"))])

    # Execute
    answer = a_desk(store, model).suggest(CONTEXT, SUGGESTION_LIMIT)

    # Assert
    assert answer == Picked(())
