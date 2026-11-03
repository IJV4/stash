import os
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TextIO
from zoneinfo import ZoneInfo

from stash.cli.failure import FAILURE, USAGE_ERROR, CommandFailed
from stash.config import ProviderName
from stash.evaluation import EvalArm, EvalCase, EvalTarget, Ocr, evaluate, load_cases, render_report

PROTECTED_SUFFIXES = frozenset({".jsonl", ".json", ".png", ".jpg", ".jpeg", ".webp", ".gif"})


@dataclass(frozen=True, slots=True)
class EvalRequest:
    providers: tuple[str, ...] | None
    arms: tuple[EvalArm, ...]
    cases: Path
    out: Path | None


def run_eval_command(
    request: EvalRequest,
    targets: Mapping[ProviderName, EvalTarget],
    ocr: Ocr,
    clock: Callable[[], datetime],
    timezone: ZoneInfo,
    out: TextIO,
) -> int:
    _check_out(request)
    chosen = _chosen(request.providers, targets)
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


def _chosen(
    providers: tuple[str, ...] | None, targets: Mapping[ProviderName, EvalTarget]
) -> list[EvalTarget]:
    names = (
        [name.value for name in ProviderName if name in targets] if providers is None else providers
    )
    by_name = {name.value: target for name, target in targets.items()}
    for name in names:
        if name not in by_name:
            raise CommandFailed(f"provider {name} is not configured", USAGE_ERROR)
    return [by_name[name] for name in dict.fromkeys(names)]


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
