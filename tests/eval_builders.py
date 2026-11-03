from pathlib import Path
from typing import Any

from stash.domain import ItemType, Route, Stage
from stash.evaluation import (
    CaseKind,
    CaseResult,
    EvalArm,
    EvalCase,
    EvalField,
    Expectation,
)


def an_expectation(**overrides: Any) -> Expectation:
    fields: dict[str, Any] = {"route": Route.CAPTURE}
    return Expectation(**{**fields, **overrides})


def a_text_case(**overrides: Any) -> EvalCase:
    fields: dict[str, Any] = {
        "id": "t01",
        "kind": CaseKind.TEXT,
        "text": "Ramen Ichiban in Shibuya, Tokyo",
        "link": None,
        "image_path": None,
        "expect": an_expectation(item_type=ItemType.PLACE, stage=Stage.WANT_TO),
    }
    return EvalCase(**{**fields, **overrides})


def an_image_case(**overrides: Any) -> EvalCase:
    fields: dict[str, Any] = {
        "id": "i01",
        "kind": CaseKind.IMAGE,
        "text": "save this",
        "link": None,
        "image_path": Path("images/recipe_card.png"),
        "expect": an_expectation(item_type=ItemType.RECIPE),
    }
    return EvalCase(**{**fields, **overrides})


def a_result(**overrides: Any) -> CaseResult:
    fields: dict[str, Any] = {
        "case_id": "t01",
        "arm": EvalArm.TEXT,
        "passed_fields": frozenset({EvalField.ROUTE}),
        "failed_fields": frozenset(),
        "latency_s": 1.0,
        "error": None,
    }
    return CaseResult(**{**fields, **overrides})
