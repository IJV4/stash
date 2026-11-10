from stash.domain import Item
from stash.people.directory import PeopleDirectory
from stash.store.port import Store


class PeopleLinker:
    def __init__(self, directory: PeopleDirectory, links: Store) -> None:
        self._directory = directory
        self._links = links

    def link(self, item: Item) -> None:
        for person in self._directory.resolve(item.people):
            self._links.link(item.id, person.id)
