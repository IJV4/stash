import base64
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from stash.domain import printable_and_clip, require_text
from stash.enrich import LinkInfo
from stash.evaluation.case_json import (
    Fields,
    member,
    parse_expectation,
    parse_image_path,
    parse_link,
    text_of,
)
from stash.evaluation.expectation import Expectation
from stash.llm import ImagePart

CASE_ID_LIMIT = 64
IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


class CaseKind(StrEnum):
    TEXT = "text"
    IMAGE = "image"


@dataclass(frozen=True, slots=True)
class EvalCase:
    id: str
    kind: CaseKind
    text: str
    link: LinkInfo | None
    image_path: Path | None
    expect: Expectation

    def __post_init__(self) -> None:
        require_text("id", self.id)
        if self.kind is CaseKind.IMAGE and self.image_path is None:
            raise ValueError("an image case needs an image file")
        if self.kind is CaseKind.TEXT and self.image_path is not None:
            raise ValueError("a text case cannot have an image file")
        if self.image_path is not None and _media_type(self.image_path) is None:
            raise ValueError(f"unsupported image type: {self.image_path.suffix or 'none'}")

    def image_file(self) -> Path:
        if self.image_path is None:
            raise ValueError(f"case {self.id} has no image file")
        return self.image_path

    def image_part(self, data: bytes) -> ImagePart:
        media_type = _media_type(self.image_file())
        return ImagePart(f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}")


def _media_type(path: Path) -> str | None:
    return IMAGE_MEDIA_TYPES.get(path.suffix.lower())


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = _parse_case(line, path.parent)
            if case.id in seen:
                raise ValueError(f"duplicate id {case.id!r}")
        except ValueError as error:
            raise ValueError(f"line {number}: {error}") from error
        seen.add(case.id)
        cases.append(case)
    return cases


def _decode(line: str) -> object:
    try:
        return json.loads(line)
    except RecursionError:
        raise ValueError("JSON is nested too deeply") from None


def _parse_case(line: str, directory: Path) -> EvalCase:
    fields = Fields(_decode(line), "case")
    case = EvalCase(
        id=printable_and_clip(text_of(fields.required("id"), "id"), CASE_ID_LIMIT),
        kind=member(CaseKind, fields.required("arm"), "arm"),
        text=text_of(fields.required("text"), "text"),
        link=parse_link(fields.optional("link")),
        image_path=parse_image_path(fields.optional("image"), directory),
        expect=parse_expectation(fields.required("expect")),
    )
    fields.finish()
    return case
