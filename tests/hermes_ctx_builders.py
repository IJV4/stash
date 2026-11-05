from typing import Any

from fakes.hermes_ctx import FakeHermesContext
from hermes_events import OWNER_ID

from stash.hermes_adapter.owners import Owners


def a_hermes_context(**overrides: Any) -> FakeHermesContext:
    fields: dict[str, Any] = {"owners": Owners.parse(OWNER_ID)}
    return FakeHermesContext(**{**fields, **overrides})
