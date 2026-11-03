import pytest

from stash.capture.callbacks import TELEGRAM_CALLBACK_LIMIT, FixAction, FixKind
from stash.domain import ItemType, Stage
from stash.domain.wire import MAX_ID_LENGTH

FROZEN_WIRE_SAMPLES = [
    "stash:t:0123456789abcdef0123456789abcdef",
    "stash:s:0123456789abcdef0123456789abcdef",
    "stash:T:0123456789abcdef0123456789abcdef:recipe",
    "stash:S:0123456789abcdef0123456789abcdef:want_to",
    "stash:q:0123456789abcdef0123456789abcdef",
]


@pytest.mark.parametrize(
    ("action", "wire"),
    [
        (FixAction(FixKind.TYPE_MENU, "i1"), "stash:t:i1"),
        (FixAction(FixKind.STAGE_MENU, "i1"), "stash:s:i1"),
        (FixAction(FixKind.SET_TYPE, "i1", "recipe"), "stash:T:i1:recipe"),
        (FixAction(FixKind.SET_STAGE, "i1", "want_to"), "stash:S:i1:want_to"),
        (FixAction(FixKind.QUESTION, "c1"), "stash:q:c1"),
    ],
)
def test_each_kind_encodes_to_its_stable_wire_format(action: FixAction, wire: str) -> None:
    # Execute / Assert
    assert action.encode() == wire


@pytest.mark.parametrize("wire", FROZEN_WIRE_SAMPLES)
def test_a_frozen_sample_of_every_wire_format_parses_back_to_the_same_string(wire: str) -> None:
    # Execute
    parsed = FixAction.parse(wire)

    # Assert
    assert parsed is not None and parsed.encode() == wire


def test_parse_reads_kind_subject_and_argument_from_a_set_type_string() -> None:
    # Execute
    parsed = FixAction.parse("stash:T:i1:recipe")

    # Assert
    assert parsed == FixAction(FixKind.SET_TYPE, "i1", "recipe")


@pytest.mark.parametrize(
    "data",
    [
        "",
        "garbage",
        "stash:zz",
        "stash:zz:i1",
        "stash",
        "stash:t",
        "stash:t:",
        "other:t:i1",
        "stash:t:i1:extra",
        "stash:q:i1:extra",
        "stash:T:i1",
        "stash:T:i1:",
        "stash:T::recipe",
        "stash:S:i1:want_to:extra",
        "STASH:t:i1",
        "stash:t:i1\n",
        "stash:t: ",
    ],
)
def test_parse_returns_none_for_anything_that_is_not_a_known_wire_string(data: str) -> None:
    # Execute / Assert
    assert FixAction.parse(data) is None


def test_encode_refuses_data_over_the_telegram_limit_counted_in_utf8_bytes() -> None:
    # Setup
    action = FixAction(FixKind.TYPE_MENU, "a" * TELEGRAM_CALLBACK_LIMIT)

    # Execute / Assert
    with pytest.raises(ValueError, match="64 bytes"):
        action.encode()


def test_encode_accepts_data_of_exactly_the_telegram_limit() -> None:
    # Setup
    action = FixAction(FixKind.TYPE_MENU, "a" * (TELEGRAM_CALLBACK_LIMIT - len("stash:t:")))

    # Execute
    wire = action.encode()

    # Assert
    assert len(wire.encode("utf-8")) == TELEGRAM_CALLBACK_LIMIT


@pytest.mark.parametrize(
    ("kind", "subject_id", "argument"),
    [
        (FixKind.TYPE_MENU, "", None),
        (FixKind.TYPE_MENU, "a:b", None),
        (FixKind.TYPE_MENU, "i1", "recipe"),
        (FixKind.SET_TYPE, "i1", None),
        (FixKind.SET_TYPE, "i1", ""),
        (FixKind.SET_STAGE, "i1", "want:to"),
    ],
)
def test_a_fix_action_that_could_not_survive_the_wire_is_refused(
    kind: FixKind, subject_id: str, argument: str | None
) -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="fix action"):
        FixAction(kind, subject_id, argument)


LONGEST_ARGUMENT = max(len(member.value) for member in (*ItemType, *Stage))


@pytest.mark.parametrize("kind", [FixKind.SET_TYPE, FixKind.SET_STAGE])
def test_the_longest_callback_for_a_maximum_length_capture_id_fits_telegrams_limit(
    kind: FixKind,
) -> None:
    # Setup
    action = FixAction(kind, "i" * MAX_ID_LENGTH, "a" * LONGEST_ARGUMENT)

    # Execute
    size = len(action.encode().encode("utf-8"))

    # Assert
    assert size <= TELEGRAM_CALLBACK_LIMIT


LONGEST_ARGUMENT_VALUE = max((*ItemType, *Stage), key=lambda member: len(member.value)).value


@pytest.mark.parametrize("kind", list(FixKind))
def test_the_longest_callback_of_every_kind_for_a_maximum_length_id_fits_in_64_bytes(
    kind: FixKind,
) -> None:
    # Setup
    argument = LONGEST_ARGUMENT_VALUE if kind.takes_argument else None
    action = FixAction(kind, "x" * MAX_ID_LENGTH, argument)

    # Execute
    encoded = action.encode()

    # Assert
    assert len(encoded.encode("utf-8")) <= TELEGRAM_CALLBACK_LIMIT


def test_a_fix_action_with_a_non_ascii_subject_is_refused_because_telegram_counts_bytes() -> None:
    # Execute / Assert
    with pytest.raises(ValueError, match="fix action"):
        FixAction(FixKind.TYPE_MENU, "é")


@pytest.mark.parametrize(
    ("subject_id", "argument"),
    [("a:b", None), ("i1", "want:to")],
)
def test_a_refused_fix_action_says_the_part_must_be_printable_ascii(
    subject_id: str, argument: str | None
) -> None:
    # Setup
    kind = FixKind.TYPE_MENU if argument is None else FixKind.SET_STAGE

    # Execute / Assert
    with pytest.raises(ValueError, match="printable ASCII"):
        FixAction(kind, subject_id, argument)
