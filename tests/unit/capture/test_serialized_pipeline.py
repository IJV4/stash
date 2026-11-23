import threading
from collections.abc import Iterator

from builders import a_capture
from fakes.recording_intake import RecordingIntake

from stash.capture import SerializedPipeline
from stash.domain import RawCapture

LIVE_WAIT_SECONDS = 2.0


def test_a_live_message_is_not_kept_waiting_between_the_captures_of_a_retry_batch() -> None:
    # Setup
    pipeline = SerializedPipeline(RecordingIntake())
    live_finished: list[bool] = []

    def live_capture_is_processed() -> bool:
        worker = threading.Thread(target=lambda: pipeline.process(a_capture(text="Ramen")))
        worker.start()
        worker.join(LIVE_WAIT_SECONDS)
        return not worker.is_alive()

    def batch() -> Iterator[RawCapture]:
        yield a_capture(id="c1")
        live_finished.append(live_capture_is_processed())
        yield a_capture(id="c2")

    # Execute
    results = pipeline.retry(batch())

    # Assert
    assert (live_finished, len(results)) == ([True], 2)
