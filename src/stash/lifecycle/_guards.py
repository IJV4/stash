from collections.abc import Iterator
from contextlib import contextmanager

from stash.domain import GROUPS_ONE_LEVEL_DEEP, Item
from stash.lifecycle.errors import LifecycleRefused, StashBusy, UnknownItem
from stash.store.port import (
    ChildHoldsItemsError,
    ParentIsGroupedError,
    StoreBusyError,
    UnknownItemError,
)

CHILD_ALREADY_HOLDS_ITEMS = "{rule}: {title} already holds items"


@contextmanager
def refusing_what_the_domain_refuses() -> Iterator[None]:
    try:
        yield
    except ValueError as error:
        raise LifecycleRefused(str(error)) from error


@contextmanager
def translating_store_errors() -> Iterator[None]:
    try:
        yield
    except UnknownItemError as error:
        raise UnknownItem(error.item_id) from error
    except StoreBusyError as error:
        raise StashBusy from error


@contextmanager
def refusing_what_the_store_refuses_for_a_group(child: Item) -> Iterator[None]:
    try:
        yield
    except ParentIsGroupedError as error:
        raise LifecycleRefused(GROUPS_ONE_LEVEL_DEEP) from error
    except ChildHoldsItemsError as error:
        refusal = CHILD_ALREADY_HOLDS_ITEMS.format(rule=GROUPS_ONE_LEVEL_DEEP, title=child.title)
        raise LifecycleRefused(refusal) from error
