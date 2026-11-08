import pytest

from stash.domain import Stage

CLOSED_BY_STAGE = [
    pytest.param(Stage.INBOX, False, id="inbox"),
    pytest.param(Stage.WANT_TO, False, id="want_to"),
    pytest.param(Stage.PLANNED, False, id="planned"),
    pytest.param(Stage.DOING, False, id="doing"),
    pytest.param(Stage.DONE, True, id="done"),
    pytest.param(Stage.DROPPED, True, id="dropped"),
]


def test_the_closed_table_covers_every_stage() -> None:
    # Execute / Assert
    assert {param.values[0] for param in CLOSED_BY_STAGE} == set(Stage)
