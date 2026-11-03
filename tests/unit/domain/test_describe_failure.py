from stash.domain import describe_failure


def test_a_failure_with_a_message_is_described_as_type_name_and_message() -> None:
    # Execute / Assert
    assert describe_failure(KeyError("boom")) == "KeyError: 'boom'"


def test_a_failure_with_a_blank_message_is_described_by_type_name_alone() -> None:
    # Execute / Assert
    assert describe_failure(RuntimeError("  ")) == "RuntimeError"


def test_a_failure_without_arguments_is_described_by_type_name_alone() -> None:
    # Execute / Assert
    assert describe_failure(TimeoutError()) == "TimeoutError"


def test_whitespace_runs_in_the_message_collapse_to_single_spaces() -> None:
    # Execute / Assert
    assert describe_failure(ValueError("a \n\t b")) == "ValueError: a b"
