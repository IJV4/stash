from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fakes.chat_model import FakeChatModel
from fakes.ocr import FakeOcr

from stash.evaluation import EvalArm, EvalCase, EvalRun, EvalTarget, Ocr, run_eval
from stash.llm import ChatModel

NOON_UTC = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
IMAGE_BYTES = b"fake png bytes"


def an_answer(**overrides: Any) -> dict[str, object]:
    fields: dict[str, object] = {
        "route": "capture",
        "item_type": "place",
        "title": "Ramen Ichiban",
        "stage": "want_to",
        "details": {},
        "tags": [],
        "people": [],
        "date": None,
    }
    return {**fields, **overrides}


def read_fake_image(path: Path) -> bytes:
    return IMAGE_BYTES


def run_cases(
    cases: Sequence[EvalCase],
    model: ChatModel | None = None,
    arms: Sequence[EvalArm] = (EvalArm.TEXT,),
    ocr: Ocr | None = None,
    vision_model: ChatModel | None = None,
    **options: Any,
) -> EvalRun:
    target = EvalTarget(
        "local", FakeChatModel(an_answer()) if model is None else model, vision_model
    )
    clock: Callable[[], datetime] = options.pop("clock", lambda: NOON_UTC)
    return run_eval(
        cases,
        target,
        arms,
        FakeOcr() if ocr is None else ocr,
        clock,
        read_image=options.pop("read_image", read_fake_image),
        timezone=options.pop("timezone", UTC_ZONE),
        **options,
    )


UTC_ZONE = ZoneInfo("UTC")
LOS_ANGELES = ZoneInfo("America/Los_Angeles")
