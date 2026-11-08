from fakes.store_factories import FreshStore

from stash.domain import Item, Outcome, Step


class VanishingItemStore(FreshStore):
    def __init__(self) -> None:
        super().__init__()
        self._vanishing_items: set[str] = set()
        self._vanishing_outcomes: set[str] = set()
        self._vanishing_after_saving: set[str] = set()
        self._vanishing_after_listing_steps: set[str] = set()

    def vanish_after_reading_item(self, item_id: str) -> None:
        self._vanishing_items.add(item_id)

    def vanish_item_after_reading_outcome(self, outcome_id: str) -> None:
        self._vanishing_outcomes.add(outcome_id)

    def vanish_item_after_saving_outcome(self, outcome_id: str) -> None:
        self._vanishing_after_saving.add(outcome_id)

    def vanish_item_after_listing_open_steps(self, item_id: str) -> None:
        self._vanishing_after_listing_steps.add(item_id)

    def get_item(self, item_id: str) -> Item | None:
        item = super().get_item(item_id)
        if item_id in self._vanishing_items:
            self._vanishing_items.discard(item_id)
            self.delete_item(item_id)
        return item

    def get_outcome(self, outcome_id: str) -> Outcome | None:
        outcome = super().get_outcome(outcome_id)
        if outcome is not None and outcome_id in self._vanishing_outcomes:
            self._vanishing_outcomes.discard(outcome_id)
            self.delete_item(outcome.item_id)
        return outcome

    def save_outcome(self, outcome: Outcome) -> None:
        super().save_outcome(outcome)
        if outcome.id in self._vanishing_after_saving:
            self._vanishing_after_saving.discard(outcome.id)
            self.delete_item(outcome.item_id)

    def open_confirmed_steps(self) -> list[Step]:
        steps = super().open_confirmed_steps()
        for item_id in self._vanishing_after_listing_steps:
            self.delete_item(item_id)
        self._vanishing_after_listing_steps.clear()
        return steps
