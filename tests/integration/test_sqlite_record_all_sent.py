import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from builders import BASE
from fakes.store_factories import opened
from step_builders import a_nudge

REFUSED_SUBJECT = "refused"
REFUSAL = "ledger refused the row"
REFUSE_ONE_SUBJECT = f"""
CREATE TRIGGER refuse_one_subject BEFORE INSERT ON sent_nudges
WHEN NEW.subject_id = '{REFUSED_SUBJECT}'
BEGIN SELECT RAISE(ABORT, '{REFUSAL}'); END
"""


def install_the_refusing_trigger(path: Path) -> None:
    with closing(sqlite3.connect(path, isolation_level=None)) as side:
        side.execute(REFUSE_ONE_SUBJECT)


@pytest.mark.integration
def test_a_row_the_ledger_refuses_raises_the_refusal_to_the_caller(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as store:
        install_the_refusing_trigger(path)
        nudges = [a_nudge(subject_id="fine"), a_nudge(subject_id=REFUSED_SUBJECT)]

        # Execute / Assert
        with pytest.raises(sqlite3.IntegrityError, match=REFUSAL):
            store.record_all_sent(nudges, BASE)


@pytest.mark.integration
def test_a_row_the_ledger_refuses_leaves_the_rows_before_it_unrecorded(tmp_path: Path) -> None:
    # Setup
    path = tmp_path / "stash.db"
    with opened(path) as store:
        install_the_refusing_trigger(path)
        accepted = a_nudge(subject_id="fine")
        with pytest.raises(sqlite3.IntegrityError):
            store.record_all_sent([accepted, a_nudge(subject_id=REFUSED_SUBJECT)], BASE)

        # Execute
        sent = store.was_sent(accepted.key)

        # Assert
        assert sent is False
