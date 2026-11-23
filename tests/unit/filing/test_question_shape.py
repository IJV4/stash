import pytest
from eval_files import SHIPPED_CASES

from stash.domain import Route
from stash.evaluation import CaseKind, load_cases
from stash.filing.question_shape import looks_like_question


@pytest.mark.parametrize(
    "text",
    [
        "Saturday afternoon hike?",
        "What should I do this weekend",
        "  🍜 which books did I read this year",
        "should we go to the lake",
        "Can you find ramen near me",
        "show me my kept recipes",
        "see https://example.com/a?b=1 what do you think?",
    ],
)
def test_text_shaped_like_a_question_is_recognised(text: str) -> None:
    # Execute
    result = looks_like_question(text)

    # Assert
    assert result is True


@pytest.mark.parametrize(
    "text",
    [
        "what I learned from the sleep episode",
        "how to fold a fitted sheet",
        "what a view",
        "list my books",
        "I have 2 h free Saturday",
        "try this https://www.youtube.com/watch?v=fake0001",
        "can opener on sale",
        "",
    ],
)
def test_statements_imperatives_and_links_with_query_strings_are_not_questions(text: str) -> None:
    # Execute
    result = looks_like_question(text)

    # Assert
    assert result is False


def test_every_shipped_request_case_has_a_question_shape_and_no_capture_case_does() -> None:
    # Setup
    cases = [case for case in load_cases(SHIPPED_CASES) if case.kind is CaseKind.TEXT]

    # Execute
    shaped = {case.id: looks_like_question(case.text) for case in cases}

    # Assert
    assert {case.id for case in cases if shaped[case.id]} >= {
        case.id for case in cases if case.expect.route is Route.REQUEST
    }
    assert not [case.id for case in cases if case.expect.route is Route.CAPTURE and shaped[case.id]]
