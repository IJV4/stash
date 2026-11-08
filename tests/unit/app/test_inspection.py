from stash.app.inspection import INSPECTION_DEADLINE_SECONDS

VIDEO_URL = "https://www.youtube.com/watch?v=abc123"
PAGE_URL = "https://example.com/ramen-tokyo"
PAGE = "<html><head><title>Ramen Tokyo</title></head></html>"
SHORT_DEADLINE_SECONDS = 0.005


def test_the_inspection_deadline_is_25_seconds() -> None:
    # Assert
    assert INSPECTION_DEADLINE_SECONDS == 25.0
