import json
from pathlib import Path

import pytest

from stash.evaluation import EvalField, load_cases

TEXT_CASE = {
    "id": "t01",
    "arm": "text",
    "text": "Ramen Ichiban in Shibuya, Tokyo",
    "link": None,
    "expect": {
        "route": "capture",
        "item_type": "place",
        "stage": "want_to",
        "details": {"city": "Tokyo"},
    },
}
SECOND_CASE = {"id": "r01", "arm": "text", "text": "what can I do?", "expect": {"route": "request"}}
IMAGE_CASE = {
    "id": "i01",
    "arm": "image",
    "text": "save this",
    "image": "images/recipe_card.png",
    "expect": {"route": "capture"},
}
LINK = {
    "url": "https://www.youtube.com/watch?v=fake0001",
    "title": "Miso soup",
    "description": "Quick soup",
}


def write_cases(directory: Path, *lines: object) -> Path:
    path = directory / "cases.jsonl"
    path.write_text(
        "\n".join(line if isinstance(line, str) else json.dumps(line) for line in lines) + "\n"
    )
    return path


def load_message(directory: Path, *lines: object) -> str:
    with pytest.raises(ValueError, match=r"^line \d+") as raised:
        load_cases(write_cases(directory, *lines))
    return str(raised.value)


def test_omitted_expectation_fields_are_not_scored(tmp_path: Path) -> None:
    # Execute
    case = load_cases(write_cases(tmp_path, SECOND_CASE))[0]

    # Assert
    assert case.expect.scored_fields() == {EvalField.ROUTE}


def test_a_null_expectation_field_is_not_scored(tmp_path: Path) -> None:
    # Setup
    nulls = {**SECOND_CASE, "expect": {"route": "request", "stage": None, "date": None}}

    # Execute
    case = load_cases(write_cases(tmp_path, nulls))[0]

    # Assert
    assert case.expect.scored_fields() == {EvalField.ROUTE}


def test_a_link_object_becomes_link_info_with_the_platform_of_its_url(tmp_path: Path) -> None:
    # Setup
    linked = {**TEXT_CASE, "link": LINK}

    # Execute
    link = load_cases(write_cases(tmp_path, linked))[0].link

    # Assert
    assert link is not None and (link.platform, link.title, link.description) == (
        "youtube",
        "Miso soup",
        "Quick soup",
    )


def test_a_link_without_optional_fields_has_no_uploader_duration_or_captions(
    tmp_path: Path,
) -> None:
    # Setup
    linked = {**TEXT_CASE, "link": LINK}

    # Execute
    link = load_cases(write_cases(tmp_path, linked))[0].link

    # Assert
    assert link is not None and (link.uploader, link.duration_s, link.has_captions) == (
        None,
        None,
        False,
    )


def test_blank_lines_are_skipped(tmp_path: Path) -> None:
    # Execute
    cases = load_cases(write_cases(tmp_path, "", TEXT_CASE, "   ", SECOND_CASE, ""))

    # Assert
    assert [case.id for case in cases] == ["t01", "r01"]


def test_a_line_that_is_not_json_is_reported_by_its_line_number(tmp_path: Path) -> None:
    # Execute / Assert
    assert load_message(tmp_path, TEXT_CASE, "{not json").startswith("line 2")


def test_line_numbers_count_the_blank_lines(tmp_path: Path) -> None:
    # Execute / Assert
    assert load_message(tmp_path, TEXT_CASE, "", "{not json").startswith("line 3")


def test_a_line_that_is_not_a_json_object_is_rejected(tmp_path: Path) -> None:
    # Execute / Assert
    assert "must be a JSON object" in load_message(tmp_path, "[1, 2]")


def test_an_unknown_arm_is_rejected_by_name(tmp_path: Path) -> None:
    # Execute / Assert
    assert "arm 'audio'" in load_message(tmp_path, {**TEXT_CASE, "arm": "audio"})


def test_an_unknown_route_is_rejected_by_name(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "expect": {"route": "maybe"}}

    # Execute / Assert
    assert "route 'maybe'" in load_message(tmp_path, case)


def test_an_unknown_item_type_is_rejected_by_name(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "expect": {"route": "capture", "item_type": "spaceship"}}

    # Execute / Assert
    assert "item_type 'spaceship'" in load_message(tmp_path, case)


def test_a_missing_key_is_named(tmp_path: Path) -> None:
    # Setup
    case = {key: value for key, value in TEXT_CASE.items() if key != "text"}

    # Execute / Assert
    assert "missing key 'text'" in load_message(tmp_path, case)


def test_a_missing_route_is_named(tmp_path: Path) -> None:
    # Execute / Assert
    assert "missing key 'route'" in load_message(tmp_path, {**TEXT_CASE, "expect": {}})


def test_an_unknown_case_key_is_named(tmp_path: Path) -> None:
    # Execute / Assert
    assert "unknown key 'colour'" in load_message(tmp_path, {**TEXT_CASE, "colour": "red"})


def test_an_unknown_expectation_key_is_named(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "expect": {"route": "capture", "mood": "happy"}}

    # Execute / Assert
    assert "unknown key 'mood'" in load_message(tmp_path, case)


def test_an_unknown_link_key_is_named(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "link": {**LINK, "rating": 5}}

    # Execute / Assert
    assert "unknown key 'rating'" in load_message(tmp_path, case)


def test_a_link_without_a_usable_url_is_rejected(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "link": {**LINK, "url": "ftp://files.example.com/a"}}

    # Execute / Assert
    assert load_message(tmp_path, case).startswith("line 1")


def test_a_text_value_that_is_not_a_string_is_rejected(tmp_path: Path) -> None:
    # Execute / Assert
    assert "text must be a string" in load_message(tmp_path, {**TEXT_CASE, "text": 7})


def test_details_whose_values_are_not_strings_are_rejected(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "expect": {"route": "capture", "details": {"city": 7}}}

    # Execute / Assert
    assert "details must map text to text" in load_message(tmp_path, case)


def test_a_date_that_is_not_an_iso_date_is_rejected(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "expect": {"route": "capture", "date": "next friday"}}

    # Execute / Assert
    assert "date must be YYYY-MM-DD" in load_message(tmp_path, case)


def test_captions_that_are_not_a_boolean_are_rejected(tmp_path: Path) -> None:
    # Setup
    case = {**TEXT_CASE, "link": {**LINK, "has_captions": "yes"}}

    # Execute / Assert
    assert "has_captions must be true or false" in load_message(tmp_path, case)


def test_a_repeated_id_is_reported_on_the_line_that_repeats_it(tmp_path: Path) -> None:
    # Execute / Assert
    assert load_message(tmp_path, TEXT_CASE, TEXT_CASE).startswith("line 2: duplicate id 't01'")


def test_an_image_case_without_an_image_is_rejected_on_its_line(tmp_path: Path) -> None:
    # Setup
    case = {key: value for key, value in IMAGE_CASE.items() if key != "image"}

    # Execute / Assert
    assert load_message(tmp_path, TEXT_CASE, case).startswith("line 2")


def test_a_text_case_with_an_image_is_rejected_on_its_line(tmp_path: Path) -> None:
    # Execute / Assert
    assert load_message(tmp_path, {**TEXT_CASE, "image": "images/a.png"}).startswith("line 1")


@pytest.mark.parametrize("image", ["/etc/hostname", "../secrets/card.png", "images/../../a.png"])
def test_an_image_outside_the_cases_directory_is_rejected(tmp_path: Path, image: str) -> None:
    # Execute / Assert
    assert "inside the cases directory" in load_message(tmp_path, {**IMAGE_CASE, "image": image})


def test_a_deeply_nested_line_is_reported_as_a_bad_line(tmp_path: Path) -> None:
    # Setup
    nested = "[" * 100_000

    # Execute
    message = load_message(tmp_path, TEXT_CASE, nested)

    # Assert
    assert message.startswith("line 2: ")
