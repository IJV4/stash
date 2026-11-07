import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import date

from stash.hermes_adapter.people_answers import (
    key_date_answer,
    linked_answer,
    people_answer,
    person_answer,
    removed_answer,
)
from stash.hermes_adapter.people_schemas import (
    ADD_KEY_DATE_SCHEMA,
    ADD_PERSON_SCHEMA,
    LINK_PERSON_SCHEMA,
    PEOPLE_SCHEMA,
    REMOVE_PERSON_SCHEMA,
)
from stash.hermes_adapter.ports import PeopleDesk
from stash.hermes_adapter.tool_arguments import ToolArguments
from stash.hermes_adapter.tool_json import UNREADABLE, UNWRITABLE, answering
from stash.hermes_adapter.tool_spec import ToolSpec
from stash.store.port import UnknownItemError, UnknownPersonError

logger = logging.getLogger(__name__)


@contextmanager
def _refusing_unknown_ids() -> Iterator[None]:
    try:
        yield
    except UnknownPersonError as unknown:
        raise ValueError(f"no person with id {unknown.person_id!r}") from None
    except UnknownItemError as unknown:
        raise ValueError(f"no item with id {unknown.item_id!r}") from None


class PeopleTools:
    def __init__(self, desk: PeopleDesk, today: Callable[[], date]) -> None:
        self._desk = desk
        self._today = today

    def specs(self) -> tuple[ToolSpec, ...]:
        return (
            ToolSpec(PEOPLE_SCHEMA, self.people),
            ToolSpec(ADD_PERSON_SCHEMA, self.add_person),
            ToolSpec(ADD_KEY_DATE_SCHEMA, self.add_key_date),
            ToolSpec(LINK_PERSON_SCHEMA, self.link_person),
            ToolSpec(REMOVE_PERSON_SCHEMA, self.remove_person),
        )

    def people(self, args: object, **kwargs: object) -> str:
        return answering(args, UNREADABLE, self._people, logger)

    def add_person(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._add_person, logger)

    def add_key_date(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._add_key_date, logger)

    def link_person(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._link_person, logger)

    def remove_person(self, args: object, **kwargs: object) -> str:
        return answering(args, UNWRITABLE, self._remove_person, logger)

    def _people(self, arguments: ToolArguments) -> str:
        return people_answer(self._desk.roster(self._today()))

    def _add_person(self, arguments: ToolArguments) -> str:
        person = self._desk.add(
            arguments.required_text("name"),
            arguments.optional_text("relation"),
            arguments.optional_aliases(),
        )
        return person_answer(person)

    def _add_key_date(self, arguments: ToolArguments) -> str:
        with _refusing_unknown_ids():
            key_date = self._desk.add_key_date(
                arguments.required_id("person_id"),
                arguments.key_date_kind(),
                arguments.required_int("month"),
                arguments.required_int("day"),
                arguments.optional_year(),
                arguments.optional_text("label"),
            )
        return key_date_answer(key_date)

    def _link_person(self, arguments: ToolArguments) -> str:
        item_id = arguments.required_id("item_id")
        person_id = arguments.required_id("person_id")
        with _refusing_unknown_ids():
            self._desk.link(item_id, person_id)
        return linked_answer(item_id, person_id)

    def _remove_person(self, arguments: ToolArguments) -> str:
        person_id = arguments.required_id("person_id")
        with _refusing_unknown_ids():
            self._desk.remove(person_id)
        return removed_answer(person_id)
