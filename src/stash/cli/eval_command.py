import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from stash.cli.failure import FAILURE, USAGE_ERROR, CommandFailed
from stash.config import Thinking
from stash.evaluation import (
    EvalArm,
    EvalCase,
    EvalTarget,
    EvalTargets,
    Ocr,
    UnconfiguredProviderError,
    evaluate,
    load_cases,
    render_report,
)

PROTECTED_SUFFIXES = frozenset({".jsonl", ".json", ".png", ".jpg", ".jpeg", ".webp", ".gif"})


@dataclass(frozen=True, slots=True)
class EvalRequest:
    providers: tuple[str, ...] | None
    thinking: tuple[Thinking, ...] | None
    arms: tuple[EvalArm, ...]
    cases: Path
    out: Path | None


def run_eval_command(
    request: EvalRequest,
    targets: EvalTargets,
    ocr: Ocr,
    clock: Callable[[], datetime],
    timezone: ZoneInfo,
    out: TextIO,
) -> int:
    _check_out(request)
    chosen = _chosen(request, targets)
    cases = _load(request.cases)
    runs = evaluate(cases, chosen, request.arms, ocr, clock, timezone=timezone)
    report = render_report(runs)
    print(report, file=out)
    if request.out is not None:
        _save(report, request.out)
    return 0


def _check_out(request: EvalRequest) -> None:
    path = request.out
    if path is None:
        return
    if path.resolve() == request.cases.resolve():
        raise CommandFailed(f"--out {path} is the cases file", USAGE_ERROR)
    if path.suffix.lower() in PROTECTED_SUFFIXES:
        raise CommandFailed(f"--out {path} would overwrite a cases or image file", USAGE_ERROR)


def _chosen(request: EvalRequest, targets: EvalTargets) -> tuple[EvalTarget, ...]:
    try:
        return targets.select(request.providers, request.thinking)
    except UnconfiguredProviderError as error:
        raise CommandFailed(str(error), USAGE_ERROR) from error


def _load(path: Path) -> list[EvalCase]:
    try:
        return load_cases(path)
    except (OSError, ValueError) as error:
        raise CommandFailed(str(error), USAGE_ERROR) from error


def _save(report: str, path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _replace_atomically(path, report + "\n")
    except OSError as error:
        raise CommandFailed(f"cannot write {path}: {error}", FAILURE) from error


def _replace_atomically(path: Path, text: str) -> None:
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".stash-eval-")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(text)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
