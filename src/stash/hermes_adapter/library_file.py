import asyncio
import logging
from datetime import date

from stash.hermes_adapter.outbox import FileSender
from stash.hermes_adapter.ports import LibraryDocuments

logger = logging.getLogger(__name__)

MAX_DOCUMENT_BYTES = 45 * 1000 * 1000
LIBRARY_CAPTION = "📚 Your stash library"
LIBRARY_SENT = "Library sent."
LIBRARY_TOO_BIG = "Library too big to send — the copy is kept on the PC."
LIBRARY_NOT_SENT = "Could not send the library file."
NO_CHAT_FOR_LIBRARY = "No owner chat is set, so there is nowhere to send the library file."


def library_filename(day: date) -> str:
    return f"stash-library-{day.isoformat()}.html"


class LibraryFile:
    def __init__(
        self,
        documents: LibraryDocuments,
        files: FileSender,
        owner_chat: str | None,
        max_bytes: int = MAX_DOCUMENT_BYTES,
    ) -> None:
        self._documents = documents
        self._files = files
        self._owner_chat = owner_chat
        self._max_bytes = max_bytes

    async def send(self) -> str:
        if self._owner_chat is None:
            return NO_CHAT_FOR_LIBRARY
        try:
            return await self._render_and_send(self._owner_chat)
        except Exception:
            logger.exception("could not send the library file to chat %s", self._owner_chat)
            return LIBRARY_NOT_SENT

    async def _render_and_send(self, chat: str) -> str:
        day, data = await asyncio.to_thread(self._prepare)
        if len(data) > self._max_bytes:
            return LIBRARY_TOO_BIG
        await self._files.send_file(chat, library_filename(day), data, LIBRARY_CAPTION)
        return LIBRARY_SENT

    def _prepare(self) -> tuple[date, bytes]:
        library = self._documents.rendered_library()
        data = library.encoded()
        self._documents.keep_library_copy(data)
        return library.day, data
