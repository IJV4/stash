from builders import an_item
from fakes.fake_suggestion_desk import FakeSuggestionDesk

from stash.domain import Pick
from stash.suggestions import Picked, QuietPicks, Unavailable


def test_quiet_picks_are_the_picks_the_desk_answered() -> None:
    # Setup
    picks = (Pick(an_item(id="a"), "first"), Pick(an_item(id="b"), "second"))

    # Execute
    quiet = QuietPicks(FakeSuggestionDesk(Picked(picks))).picks("coming week", 3)

    # Assert
    assert quiet == picks


def test_quiet_picks_are_empty_when_the_desk_is_unavailable() -> None:
    # Execute
    quiet = QuietPicks(FakeSuggestionDesk(Unavailable())).picks("coming week", 3)

    # Assert
    assert quiet == ()


def test_quiet_picks_ask_the_desk_with_the_context_and_limit_given() -> None:
    # Setup
    desk = FakeSuggestionDesk(Picked(()))

    # Execute
    QuietPicks(desk).picks("coming week", 2)

    # Assert
    assert desk.asked == [("coming week", 2)]
