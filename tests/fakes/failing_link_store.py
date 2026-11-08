from fakes.store_factories import FreshStore


class LinkFailed(Exception):
    pass


class FailingLinkStore(FreshStore):
    def link(self, item_id: str, person_id: str) -> None:
        raise LinkFailed(f"{item_id} -> {person_id}")
