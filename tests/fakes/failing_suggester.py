from stash.suggestions import Picked, Unavailable


class FailingSuggester:
    def __init__(self, error: Exception) -> None:
        self._error = error

    def suggest(self, context: str, limit: int) -> Picked | Unavailable:
        raise self._error
