from fakes.memory_store import MemoryStore


class LinkFailed(Exception):
    pass


class FailingLinkStore(MemoryStore):
    def link(self, item_id: str, person_id: str) -> None:
        raise LinkFailed(f"{item_id} -> {person_id}")
