import asyncio

from app_builders import an_app, stored
from builders import BASE, a_capture, an_item, an_outcome, minutes_after
from capture_builders import FORCED_QUESTION, a_filing_answer, a_message
from capture_rig import build_rig
from hermes_registration_rig import register_stash
from hermes_rig import app_over, called

from stash.domain import ItemType, Stage


def test_list_prints_the_newest_items_as_type_title_and_stage() -> None:
    # Setup
    older = an_item(
        id="i1",
        capture_id="c1",
        item_type=ItemType.PLACE,
        title="Ichiran ramen",
        stage=Stage.WANT_TO,
        created_at=BASE,
    )
    newer = an_item(
        id="i2",
        capture_id="c2",
        item_type=ItemType.RECIPE,
        title="Miso soup",
        stage=Stage.INBOX,
        created_at=minutes_after(5),
    )
    plugin = register_stash(an_app(store=stored(older, newer)))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["list"], ""))

    # Assert
    assert text.splitlines() == ["Recipes · Miso soup · Inbox", "Places · Ichiran ramen · Want to"]


def test_gpu_off_status_and_on_answer_and_act_as_the_stash_gpu_command_does() -> None:
    # Setup
    plugin = register_stash(an_app())

    async def scenario() -> list[str]:
        return [
            await called(plugin.ctx.commands["gpu"], argument)
            for argument in ("off", "status", "on", "status")
        ]

    # Execute
    answers = asyncio.run(scenario())

    # Assert
    assert answers == [
        "GPU switched off until 08:00",
        "GPU busy — turned off until 08:00",
        "GPU switched on",
        "GPU free — GPU is free",
    ]


def test_retry_files_the_pending_captures_one_line_each_and_then_finds_nothing_pending() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    rig.store.add_capture(a_capture(text="Ichiran ramen in Fukuoka"))
    plugin = register_stash(app_over(rig))

    async def scenario() -> list[str]:
        return [await called(plugin.ctx.commands["retry"], "") for _ in range(2)]

    # Execute
    answers = asyncio.run(scenario())

    # Assert
    assert answers == ["filed — Places · Ichiran ramen · Want to", "Nothing pending."]


def test_retry_command_answers_a_pending_question_as_a_request_and_asks_the_ai_nothing() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    rig.pipeline.receive(a_message(FORCED_QUESTION))
    plugin = register_stash(app_over(rig))

    async def scenario() -> list[str]:
        return [await called(plugin.ctx.commands["retry"], "") for _ in range(2)]

    # Execute
    answers = asyncio.run(scenario())

    # Assert
    assert (answers, rig.model.calls, rig.store.list_items()) == (
        [f"request — {FORCED_QUESTION} — send it again starting with ? to ask", "Nothing pending."],
        [],
        [],
    )


def test_library_with_a_type_lists_only_the_kept_items_of_that_type_with_their_rating() -> None:
    # Setup
    kept_soup = an_item(
        id="r1",
        capture_id="c1",
        item_type=ItemType.RECIPE,
        title="Miso soup",
        stage=Stage.DONE,
        kept=True,
    )
    skipped_stew = an_item(
        id="r2", capture_id="c2", item_type=ItemType.RECIPE, title="Stew", stage=Stage.DONE
    )
    kept_book = an_item(
        id="b1", capture_id="c3", item_type=ItemType.BOOK, title="Dune", stage=Stage.DONE, kept=True
    )
    store = stored(kept_soup, skipped_stew, kept_book)
    for item in (kept_soup, skipped_stew, kept_book):
        store.add_outcome(an_outcome(id=f"o-{item.id}", item_id=item.id, rating=4))
    plugin = register_stash(an_app(store=store))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["library"], "recipe"))

    # Assert
    assert text == "📚 Recipes: Miso soup · ⭐4"


def test_library_with_a_plural_label_lists_only_the_kept_items_of_that_type() -> None:
    # Setup
    kept_soup = an_item(
        id="r1",
        capture_id="c1",
        item_type=ItemType.RECIPE,
        title="Miso soup",
        stage=Stage.DONE,
        kept=True,
    )
    kept_book = an_item(
        id="b1", capture_id="c3", item_type=ItemType.BOOK, title="Dune", stage=Stage.DONE, kept=True
    )
    store = stored(kept_soup, kept_book)
    for item in (kept_soup, kept_book):
        store.add_outcome(an_outcome(id=f"o-{item.id}", item_id=item.id, rating=4))
    plugin = register_stash(an_app(store=store))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["library"], "recipes"))

    # Assert
    assert text == "📚 Recipes: Miso soup · ⭐4"


def test_find_lists_items_whose_title_or_note_match() -> None:
    # Setup
    by_title = an_item(id="i1", capture_id="c1", title="Ichiran ramen", created_at=BASE)
    by_note = an_item(
        id="i2", capture_id="c2", title="Soup", note="try the ramen place", created_at=BASE
    )
    other = an_item(id="i3", capture_id="c3", title="Tax forms", created_at=BASE)
    plugin = register_stash(an_app(store=stored(by_title, by_note, other)))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["find"], "ramen"))

    # Assert
    assert sorted(line.split(" · ")[1] for line in text.splitlines()) == ["Ichiran ramen", "Soup"]


def test_find_ignores_spaces_around_what_was_typed() -> None:
    # Setup
    item = an_item(id="i1", capture_id="c1", title="Ichiran ramen", created_at=BASE)
    plugin = register_stash(an_app(store=stored(item)))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["find"], "ramen "))

    # Assert
    assert "Ichiran ramen" in text


def test_find_with_no_words_shows_the_usage_line() -> None:
    # Setup
    plugin = register_stash(an_app())

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["find"], "  "))

    # Assert
    assert text == "Usage: /find <words>"


def test_find_with_no_match_says_so() -> None:
    # Setup
    plugin = register_stash(an_app(store=stored(an_item(id="i1", capture_id="c1"))))

    # Execute
    text = asyncio.run(called(plugin.ctx.commands["find"], "zzzz"))

    # Assert
    assert text == "No items."
