from stash.domain import Filing, ItemType, Route, Stage
from stash.enrich.links import LinkInfo


class FakeCaptureFiler:
    def __init__(self, filing: Filing | None = None, error: Exception | None = None) -> None:
        self.filing = filing or Filing(
            route=Route.CAPTURE,
            item_type=ItemType.OTHER,
            title="Filed by the fake",
            stage=Stage.INBOX,
            details={},
            tags=(),
            people=(),
            date=None,
        )
        self.error = error
        self.fail_next: Exception | None = None
        self.calls: list[tuple[str, LinkInfo | None]] = []

    def file(self, text: str, link: LinkInfo | None) -> Filing:
        self.calls.append((text, link))
        if self.fail_next is not None:
            failure, self.fail_next = self.fail_next, None
            raise failure
        if self.error is not None:
            raise self.error
        return self.filing
