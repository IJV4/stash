import datetime as dt
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from stash.config import LlmTask
from stash.domain import Filing
from stash.evaluation.cases import CaseKind, EvalCase
from stash.evaluation.ocr import Ocr
from stash.evaluation.results import EvalArm
from stash.evaluation.target import EvalTarget
from stash.filing import Filer
from stash.llm import ChatModel


class Arm(Protocol):
    kind: EvalArm

    def applies_to(self, case: EvalCase) -> bool: ...

    def file(self, case: EvalCase) -> Filing: ...


class _OneModel:
    def __init__(self, model: ChatModel) -> None:
        self._model = model

    def model_for(self, task: LlmTask, now: dt.datetime) -> ChatModel:
        return self._model


class TextArm:
    kind = EvalArm.TEXT

    def __init__(self, filer: Filer) -> None:
        self._filer = filer

    def applies_to(self, case: EvalCase) -> bool:
        return case.kind is CaseKind.TEXT

    def file(self, case: EvalCase) -> Filing:
        return self._filer.file(case.text, case.link)


class VisionArm:
    kind = EvalArm.VISION

    def __init__(self, filer: Filer, model: ChatModel, read_image: Callable[[Path], bytes]) -> None:
        self._filer = filer
        self._model = model
        self._read_image = read_image

    def applies_to(self, case: EvalCase) -> bool:
        return case.kind is CaseKind.IMAGE

    def file(self, case: EvalCase) -> Filing:
        image = case.image_part(self._read_image(case.image_file()))
        return self._filer.file_image(image, case.text, self._model)


class OcrArm:
    kind = EvalArm.OCR

    def __init__(self, filer: Filer, ocr: Ocr) -> None:
        self._filer = filer
        self._ocr = ocr

    def applies_to(self, case: EvalCase) -> bool:
        return case.kind is CaseKind.IMAGE

    def file(self, case: EvalCase) -> Filing:
        read = self._ocr.read(case.image_file())
        text = "\n".join(part for part in (case.text, read.strip()) if part.strip())
        return self._filer.file(text, None)


def build_arms(
    arms: Sequence[EvalArm],
    target: EvalTarget,
    ocr: Ocr,
    clock: Callable[[], dt.datetime],
    timezone: ZoneInfo,
    read_image: Callable[[Path], bytes],
) -> list[Arm]:
    filer = Filer(_OneModel(target.model), clock, timezone)
    available: dict[EvalArm, Arm] = {
        EvalArm.TEXT: TextArm(filer),
        EvalArm.VISION: VisionArm(filer, target.image_model, read_image),
        EvalArm.OCR: OcrArm(filer, ocr),
    }
    return [available[arm] for arm in dict.fromkeys(arms)]
