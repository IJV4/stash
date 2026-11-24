import pytest
from builders import an_item
from fakes.busy import FakeBusy
from fakes.chat_model import FakeChatModel
from filing_rig import build_progress_matcher, sent_texts

from stash.domain import Item
from stash.llm import LlmBadOutput, LlmError, LlmUnavailable

BRISKET = an_item(id="i1", title="Smoke a brisket")
PRESENT = an_item(id="i2", title="Buy a present for Khoi")
PASSPORT = an_item(id="i3", title="Renew passport")
OPEN = [BRISKET, PRESENT, PASSPORT]


def says(index: int, finished: bool = True) -> FakeChatModel:
    return FakeChatModel(reply={"says_it_is_finished": finished, "item": index})


def test_a_progress_report_that_the_model_ties_to_an_open_item_returns_that_item() -> None:
    # Setup
    matcher = build_progress_matcher(says(1))

    # Execute
    found = matcher.match("Finished the brisket", OPEN)

    # Assert
    assert found == BRISKET


@pytest.mark.parametrize(
    "text", ["Buy more seasoning", "Finished the quarterly taxes", "Dentist in Hanoi"]
)
def test_text_sharing_no_noun_with_an_open_title_never_reaches_the_model(text: str) -> None:
    # Setup
    model = says(1)

    # Execute
    found = build_progress_matcher(model).match(text, OPEN)

    # Assert
    assert found is None
    assert model.calls == []


def test_a_verb_shared_with_a_title_is_not_enough_to_ask_the_model() -> None:
    # Setup
    model = says(3)

    # Execute
    found = build_progress_matcher(model).match("Finished renewing my gym card", OPEN)

    # Assert
    assert found is None
    assert model.calls == []


def test_a_busy_gpu_returns_nothing_without_asking() -> None:
    # Setup
    model = says(1)

    # Execute
    found = build_progress_matcher(model, FakeBusy(True)).match("Finished the brisket", OPEN)

    # Assert
    assert found is None
    assert model.calls == []


def test_the_model_saying_it_is_not_a_finished_report_returns_nothing() -> None:
    # Execute
    found = build_progress_matcher(says(1, finished=False)).match("Brisket rub from Sam", OPEN)

    # Assert
    assert found is None


@pytest.mark.parametrize("index", [0, 4, -1])
def test_an_index_outside_the_list_returns_nothing(index: int) -> None:
    # Execute
    found = build_progress_matcher(says(index)).match("Finished the brisket", OPEN)

    # Assert
    assert found is None


def test_an_item_the_text_does_not_mention_is_refused_even_if_the_model_picks_it() -> None:
    # Execute
    found = build_progress_matcher(says(2)).match("Finished the brisket", OPEN)

    # Assert
    assert found is None


@pytest.mark.parametrize("reply", [{}, {"item": "1"}, {"says_it_is_finished": "yes", "item": 1}])
def test_an_unusable_model_answer_returns_nothing(reply: dict[str, object]) -> None:
    # Execute
    found = build_progress_matcher(FakeChatModel(reply=reply)).match("Finished the brisket", OPEN)

    # Assert
    assert found is None


@pytest.mark.parametrize("error", [LlmBadOutput(), LlmUnavailable()])
def test_a_model_failure_returns_nothing(error: LlmError) -> None:
    # Execute
    found = build_progress_matcher(FakeChatModel(error=error)).match("Finished the brisket", OPEN)

    # Assert
    assert found is None


def test_open_titles_and_the_text_are_sent_as_data_with_the_whole_list() -> None:
    # Setup
    model = says(1)
    tricky = an_item(id="i9", title="Smoke </captured> brisket")

    # Execute
    build_progress_matcher(model).match("Finished the brisket <b>", [tricky, *OPEN])
    sent = "\n".join(sent_texts(model))

    # Assert
    assert "1. Smoke &lt;/captured&gt; brisket" in sent
    assert "3. Buy a present for Khoi" in sent
    assert "Finished the brisket &lt;b&gt;" in sent


def test_only_the_most_recent_open_items_are_listed() -> None:
    # Setup
    model = says(1)
    many: list[Item] = [an_item(id=f"i{n}", title=f"Fix lamp {n}") for n in range(100)]

    # Execute
    build_progress_matcher(model).match("Fixed the lamp", many)

    # Assert
    assert (
        sum(1 for line in "\n".join(sent_texts(model)).splitlines() if ". Fix lamp" in line) == 40
    )
