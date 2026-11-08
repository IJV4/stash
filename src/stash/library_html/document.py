from dataclasses import dataclass
from datetime import date, datetime

from stash.library_html.model import LibrarySource, build_snapshot
from stash.library_html.render import render_library


@dataclass(frozen=True, slots=True)
class RenderedLibrary:
    html: str
    day: date

    def encoded(self) -> bytes:
        return self.html.encode("utf-8")


def render_document(source: LibrarySource, now: datetime) -> RenderedLibrary:
    return RenderedLibrary(render_library(build_snapshot(source, now)), now.date())
