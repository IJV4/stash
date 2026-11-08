import threading

from capture_builders import a_filing_answer, a_message
from capture_rig import build_rig
from fakes.gated_chat_model import GatedChatModel

from stash.capture import Filed
from stash.domain import Stage

PRESS_DEADLINE_SECONDS = 2.0


def test_a_button_press_answers_while_filing_waits_on_the_model() -> None:
    # Setup
    model = GatedChatModel(a_filing_answer())
    model.release.set()
    rig = build_rig(model=model)
    first = rig.pipeline.handle(a_message("first", message_id="m1"))
    assert isinstance(first, Filed)
    model.release.clear()
    model.entered.clear()
    filing = threading.Thread(target=rig.pipeline.handle, args=(a_message("second", "m2"),))
    filing.start()
    assert model.entered.wait(PRESS_DEADLINE_SECONDS)
    press = threading.Thread(target=rig.fixes.apply, args=(f"stash:d:{first.item.id}",))

    # Execute
    press.start()
    press.join(PRESS_DEADLINE_SECONDS)
    answered_while_filing = not press.is_alive()
    model.release.set()
    filing.join(PRESS_DEADLINE_SECONDS)

    # Assert
    assert answered_while_filing
    item = rig.store.get_item(first.item.id)
    assert item is not None
    assert item.stage is Stage.DONE


def test_a_lifecycle_change_waits_for_a_write_held_by_another_thread() -> None:
    # Setup
    rig = build_rig(answer=a_filing_answer())
    filed = rig.pipeline.handle(a_message())
    assert isinstance(filed, Filed)
    held, release = threading.Event(), threading.Event()

    def holding_the_write() -> None:
        with rig.store.writing():
            held.set()
            release.wait(PRESS_DEADLINE_SECONDS)

    holder = threading.Thread(target=holding_the_write)
    holder.start()
    assert held.wait(PRESS_DEADLINE_SECONDS)
    press = threading.Thread(target=rig.fixes.apply, args=(f"stash:d:{filed.item.id}",))

    # Execute
    press.start()
    press.join(0.2)
    waited = press.is_alive()
    release.set()
    holder.join(PRESS_DEADLINE_SECONDS)
    press.join(PRESS_DEADLINE_SECONDS)

    # Assert
    assert waited
    item = rig.store.get_item(filed.item.id)
    assert item is not None
    assert item.stage is Stage.DONE
