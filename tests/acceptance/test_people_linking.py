from capture_builders import a_filing_answer, a_message
from capture_narrowing import handle_filed
from capture_rig import build_rig

from stash.capture import reply_for

GIFT_IDEA = "gift idea for Ana: ceramic class"
GIFT_IDEA_FILING = a_filing_answer(
    item_type="idea", title="Ceramic class for Ana", details={}, people=["Ana"]
)


def test_a_gift_idea_for_a_person_in_the_directory_is_linked_to_them() -> None:
    # Setup
    rig = build_rig(answer=GIFT_IDEA_FILING)
    ana = rig.people.add("Ana", relation="sister")

    # Execute
    filed = handle_filed(rig, a_message(GIFT_IDEA))

    # Assert
    assert rig.store.people_for(filed.item.id) == [ana]


def test_a_name_that_is_not_in_the_directory_is_not_linked() -> None:
    # Setup
    rig = build_rig(answer={**GIFT_IDEA_FILING, "people": ["Bea"]})
    rig.people.add("Ana")

    # Execute
    filed = handle_filed(rig, a_message(GIFT_IDEA))

    # Assert
    assert rig.store.people_for(filed.item.id) == []


def test_a_name_that_is_not_in_the_directory_leaves_the_confirmation_unchanged() -> None:
    # Setup
    unknown = build_rig(answer={**GIFT_IDEA_FILING, "people": ["Bea"]})
    nobody = build_rig(answer={**GIFT_IDEA_FILING, "people": []})

    # Execute
    filed = handle_filed(unknown, a_message(GIFT_IDEA))
    reply = reply_for(filed)

    # Assert
    assert (reply, unknown.store.people_for(filed.item.id), filed.item.people) == (
        reply_for(handle_filed(nobody, a_message(GIFT_IDEA))),
        [],
        ("Bea",),
    )
