import asyncio
import threading

from fakes.recording_library_documents import RecordingLibraryDocuments
from fakes.recording_outbox import RecordingOutbox, SentFile

from stash.hermes_adapter.library_file import (
    LIBRARY_CAPTION,
    LIBRARY_NOT_SENT,
    LIBRARY_TOO_BIG,
    LibraryFile,
)

CHAT = "1001"
LIBRARY_FILE_LOGGER = "stash.hermes_adapter.library_file"
HTML = "<p>café</p>"
HTML_BYTES = HTML.encode("utf-8")


def test_a_library_over_the_limit_is_refused_and_nothing_is_sent() -> None:
    # Setup
    outbox = RecordingOutbox()
    file = LibraryFile(RecordingLibraryDocuments(HTML), outbox, CHAT, len(HTML_BYTES) - 1)

    # Execute
    reply = asyncio.run(file.send())

    # Assert
    assert (reply, outbox.files) == (LIBRARY_TOO_BIG, [])


def test_a_library_at_exactly_the_limit_is_sent() -> None:
    # Setup
    outbox = RecordingOutbox()
    file = LibraryFile(RecordingLibraryDocuments(HTML), outbox, CHAT, len(HTML_BYTES))

    # Execute
    asyncio.run(file.send())

    # Assert
    assert outbox.files == [
        SentFile(CHAT, "stash-library-2026-11-02.html", HTML_BYTES, LIBRARY_CAPTION)
    ]


def test_the_limit_counts_utf8_bytes_not_characters() -> None:
    # Setup
    outbox = RecordingOutbox()
    file = LibraryFile(RecordingLibraryDocuments(HTML), outbox, CHAT, len(HTML))

    # Execute
    reply = asyncio.run(file.send())

    # Assert
    assert reply == LIBRARY_TOO_BIG


def test_a_library_too_big_to_send_is_still_kept_as_the_local_copy() -> None:
    # Setup
    documents = RecordingLibraryDocuments(HTML)
    file = LibraryFile(documents, RecordingOutbox(), CHAT, 1)

    # Execute
    asyncio.run(file.send())

    # Assert
    assert documents.kept == [HTML_BYTES]


def test_a_local_copy_that_cannot_be_written_sends_nothing_and_answers_with_an_error_line() -> None:
    # Setup
    outbox = RecordingOutbox()
    documents = RecordingLibraryDocuments(HTML, keep_failure=OSError("disk full"))
    file = LibraryFile(documents, outbox, CHAT)

    # Execute
    reply = asyncio.run(file.send())

    # Assert
    assert (reply, outbox.files) == (LIBRARY_NOT_SENT, [])


def test_the_library_is_rendered_and_kept_off_the_event_loop_thread() -> None:
    # Setup
    documents = RecordingLibraryDocuments(HTML)
    file = LibraryFile(documents, RecordingOutbox(), CHAT)

    async def scenario() -> int:
        await file.send()
        return threading.get_ident()

    # Execute
    loop_thread = asyncio.run(scenario())

    # Assert
    assert [thread != loop_thread for thread in documents.threads] == [True, True]
