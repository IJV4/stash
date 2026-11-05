from collections import Counter

from eval_files import SHIPPED_CASES, SHIPPED_IMAGES

from stash.domain import Route
from stash.evaluation import CaseKind, EvalCase, EvalField, load_cases

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def shipped_cases() -> list[EvalCase]:
    return load_cases(SHIPPED_CASES)


def test_the_shipped_cases_file_holds_thirty_one_cases() -> None:
    # Execute / Assert
    assert len(shipped_cases()) == 31


def test_the_shipped_case_ids_are_unique() -> None:
    # Execute
    ids = [case.id for case in shipped_cases()]

    # Assert
    assert len(set(ids)) == len(ids)


def is_text_filing(case: EvalCase) -> bool:
    return case.kind is CaseKind.TEXT and case.expect.scored_fields() != {EvalField.ROUTE}


def is_text_routing(case: EvalCase) -> bool:
    return case.kind is CaseKind.TEXT and case.expect.scored_fields() == {EvalField.ROUTE}


def test_seventeen_shipped_text_cases_are_filings() -> None:
    # Execute
    filings = [case for case in shipped_cases() if is_text_filing(case)]

    # Assert
    assert len(filings) == 17


def test_eleven_shipped_text_cases_are_routing_cases_scored_on_route_only() -> None:
    # Execute
    routing = [case for case in shipped_cases() if is_text_routing(case)]

    # Assert
    assert len(routing) == 11


def test_the_shipped_routing_cases_expect_seven_requests_two_unsure_and_two_captures() -> None:
    # Execute
    routes = Counter(case.expect.route for case in shipped_cases() if is_text_routing(case))

    # Assert
    assert routes == {Route.REQUEST: 7, Route.UNSURE: 2, Route.CAPTURE: 2}


def test_three_shipped_cases_are_images() -> None:
    # Execute
    images = [case for case in shipped_cases() if case.kind is CaseKind.IMAGE]

    # Assert
    assert len(images) == 3


def test_every_shipped_image_case_points_at_a_file_in_the_images_directory() -> None:
    # Execute
    parents = {case.image_file().parent for case in shipped_cases() if case.kind is CaseKind.IMAGE}

    # Assert
    assert parents == {SHIPPED_IMAGES}


def test_every_shipped_image_file_exists() -> None:
    # Execute
    missing = [
        case.image_file()
        for case in shipped_cases()
        if case.kind is CaseKind.IMAGE and not case.image_file().is_file()
    ]

    # Assert
    assert missing == []


def test_every_shipped_image_file_is_a_png() -> None:
    # Execute
    not_png = [
        case.image_file()
        for case in shipped_cases()
        if case.kind is CaseKind.IMAGE
        and not case.image_file().read_bytes().startswith(PNG_SIGNATURE)
    ]

    # Assert
    assert not_png == []
