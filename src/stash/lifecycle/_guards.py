from collections.abc import Iterator
from contextlib import contextmanager

from stash.lifecycle.errors import LifecycleRefused, UnknownItem
from stash.store.port import UnknownItemError


@contextmanager
def refusing_what_the_domain_refuses() -> Iterator[None]:
    try:
        yield
    except ValueError as error:
        raise LifecycleRefused(str(error)) from error


@contextmanager
def reporting_items_that_vanished() -> Iterator[None]:
    try:
        yield
    except UnknownItemError as error:
        raise UnknownItem(error.item_id) from error
